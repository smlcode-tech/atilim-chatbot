"""Vektör ve anahtar kelime aramalarını birleştiren hibrit getirici."""

from atilim_assistant.domain import Document
from atilim_assistant.ports import Embedder
from atilim_assistant.retrieval.lexical import LexicalIndex
from atilim_assistant.retrieval.store import DocumentStore

# Reciprocal Rank Fusion sabiti; literatürdeki standart değer.
_RRF_K = 60


class HybridRetriever:
    def __init__(
        self, store: DocumentStore, embedder: Embedder, top_k: int, max_chars: int
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._top_k = top_k
        self._max_chars = max_chars
        # Anahtar kelime indeksi açılışta bir kez kurulur; yeni indekslenen
        # belgelerin görünmesi için süreç yeniden başlatılmalıdır.
        self._lexical = LexicalIndex(store.all())

    def retrieve(self, query: str) -> list[Document]:
        semantic = self._store.search(self._embedder.embed_query(query), self._top_k)
        lexical = self._lexical.search(query, self._top_k)

        documents: dict[str, Document] = {}
        scores: dict[str, float] = {}
        for ranking in (semantic, lexical):
            for rank, document in enumerate(ranking):
                documents[document.id] = document
                scores[document.id] = scores.get(document.id, 0.0) + 1 / (_RRF_K + rank + 1)

        best = sorted(scores, key=scores.get, reverse=True)[: self._top_k]
        return self._fit([documents[document_id] for document_id in best])

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
