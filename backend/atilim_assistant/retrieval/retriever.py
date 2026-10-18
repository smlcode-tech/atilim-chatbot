"""Vektör, anahtar kelime ve soru kalıbı aramalarını birleştiren hibrit getirici."""

from atilim_assistant.domain import Document
from atilim_assistant.ports import Embedder
from atilim_assistant.retrieval.lexical import LexicalIndex
from atilim_assistant.retrieval.store import DocumentStore

# Reciprocal Rank Fusion sabiti; literatürdeki standart değer.
_RRF_K = 60

# Hazır yanıtların her biri birkaç soru kalıbıyla indekslenir; `top_k` farklı yanıta ulaşmak
# için o kadar kat fazla kalıp getirilir.
_QUESTIONS_PER_ANSWER = 8


class HybridRetriever:
    def __init__(
        self,
        store: DocumentStore,
        embedder: Embedder,
        top_k: int,
        max_chars: int,
        questions: DocumentStore | None = None,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._top_k = top_k
        self._max_chars = max_chars
        # Anahtar kelime indeksi açılışta bir kez kurulur; yeni indekslenen
        # belgelerin görünmesi için süreç yeniden başlatılmalıdır.
        self._lexical = LexicalIndex(store.all())
        # Soru kalıbı indeksi henüz kurulmamışsa (eski indeks) arama onsuz sürer.
        self._questions = questions if questions is not None and questions.count() else None

    @property
    def course_codes(self) -> frozenset[str]:
        """Belgelerde geçen ders kodları; yanlış yazılmış kodları düzeltmek için."""
        return self._lexical.course_codes

    def retrieve(self, query: str) -> list[Document]:
        embedding = self._embedder.embed_query(query)
        rankings = [
            self._store.search(embedding, self._top_k),
            self._lexical.search(query, self._top_k),
        ]
        if self._questions is not None:
            matches = self._questions.search(embedding, self._top_k * _QUESTIONS_PER_ANSWER)
            rankings.append(_distinct(matches)[: self._top_k])

        # Aynı metin hem sayfa belgesi hem hazır yanıt olarak gelebilir (kadro listesi gibi);
        # metne göre birleştirmek bağlamı tekrarla doldurmaz, iki aramanın oyunu da toplar.
        documents: dict[str, Document] = {}
        scores: dict[str, float] = {}
        for ranking in rankings:
            for rank, document in enumerate(ranking):
                documents.setdefault(document.text, document)
                scores[document.text] = scores.get(document.text, 0.0) + 1 / (_RRF_K + rank + 1)

        best = sorted(scores, key=scores.get, reverse=True)[: self._top_k]
        return self._fit([documents[text] for text in best])

    def _fit(self, ranked: list[Document]) -> list[Document]:
        """Bağlamı karakter bütçesinde tutar: sığmayan belge atlanır, sıradakiler denenir.

        Sağlayıcının istek başına token sınırı aşılırsa soru hiç yanıtlanamaz; birkaç belgeyi
        bırakmak her zaman daha iyidir.
        """
        fitted, used = [], 0
        for document in ranked:
            if used + len(document.text) <= self._max_chars:
                fitted.append(document)
                used += len(document.text)
        return fitted


def _distinct(documents: list[Document]) -> list[Document]:
    """Aynı yanıta götüren kalıplardan yalnızca en üstteki kalır."""
    distinct: dict[str, Document] = {}
    for document in documents:
        distinct.setdefault(document.text, document)
    return list(distinct.values())
