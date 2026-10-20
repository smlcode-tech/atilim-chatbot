"""Vektör, anahtar kelime ve soru kalıbı aramalarını birleştiren hibrit getirici."""

import re
from dataclasses import replace

from atilim_assistant.domain import Document
from atilim_assistant.ports import Embedder
from atilim_assistant.retrieval.lexical import LexicalIndex
from atilim_assistant.retrieval.store import DocumentStore

# Reciprocal Rank Fusion sabiti; literatürdeki standart değer.
_RRF_K = 60

# Hazır yanıtların her biri birkaç soru kalıbıyla indekslenir; `top_k` farklı yanıta ulaşmak
# için o kadar kat fazla kalıp getirilir.
_QUESTIONS_PER_ANSWER = 8

# Önerilecek soru kalıbı, soruyla ortak bir içerik sözcüğü taşımıyorsa en az bu kadar anlamca
# yakın olmalıdır. voyage-multilingual-2 ile ölçüldü: ilgisiz sorularda ("yemekhane menüsü",
# "kampüse nasıl giderim") en yakın kalıp 0.31–0.43, eşanlamlı söyleyişlerde 0.45 üzeri.
_STRONG_SIMILARITY = 0.45
# Önerilere aday olarak bakılan kalıp sayısı.
_SUGGESTION_CANDIDATES = 60
# Ders kodu ("SE212", "PÇ3") ya da sıra sayısı olmayan uzun sayı; "1." gibi sıra sayıları değil.
_CODE_LIKE = re.compile(r"[^\W\d_]\d|\d{2,}")


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
        # Öneriler için kalıpların yalnızca kendi sözcükleriyle aranan kopyası; yanıt metni
        # katılırsa her kalıp yanıtındaki sözcüklerle de eşleşirdi.
        patterns = self._questions.all() if self._questions is not None else []
        self._question_words = LexicalIndex([replace(d, text="") for d in patterns])
        # Kalıp kimliği → yanıt metni; aynı yanıta götüren kalıplardan biri önerilir.
        self._answers = {document.id: document.text for document in patterns}

    @property
    def course_codes(self) -> frozenset[str]:
        """Belgelerde geçen ders kodları; yanlış yazılmış kodları düzeltmek için."""
        return self._lexical.course_codes

    def similar_questions(self, query: str, limit: int) -> list[str]:
        """Sorguya en yakın, yanıtı olan soru kalıpları; her yanıttan ve her kalıp
        biçiminden ("X kaç AKTS?") yalnızca biri.

        Soru yanıtlanamadığında kullanıcıya seçenek olarak sunulur. Yalnızca soruyla ortak
        içerik sözcüğü taşıyan ya da anlamca çok yakın kalıplar önerilir: vektör araması
        alakasız soruya da "en yakın" bir şey döndürür, kısa sorularda ise ("staj kaç gün")
        sözcük eşleşmesini kaçırabilir.
        """
        if self._questions is None:
            return []
        scored = self._questions.search_scored(
            self._embedder.embed_query(query), _SUGGESTION_CANDIDATES
        )
        lexical = self._question_words.search(query, _SUGGESTION_CANDIDATES)
        shares_words = {document.id for document in lexical}
        similar = {document.id for document, score in scored if score >= _STRONG_SIMILARITY}

        by_id = {document.id: document for document, _ in scored}
        by_id.update({document.id: document for document in lexical})
        scores: dict[str, float] = {}
        for ranking in ([document for document, _ in scored], lexical):
            for rank, document in enumerate(ranking):
                scores[document.id] = scores.get(document.id, 0.0) + 1 / (_RRF_K + rank + 1)

        suggestions: list[str] = []
        seen_answers: set[str] = set()
        seen_shapes: set[str] = set()
        for id_ in sorted(scores, key=scores.get, reverse=True):
            if id_ not in shares_words and id_ not in similar:
                continue
            question = by_id[id_].title
            answer = self._answers.get(id_, question)
            shape = _shape(question)
            if answer in seen_answers or shape in seen_shapes:
                continue
            seen_answers.add(answer)
            seen_shapes.add(shape)
            suggestions.append(question)
            if len(suggestions) == limit:
                break
        return suggestions

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


def _shape(question: str) -> str:
    """Kalıbın biçimi: ders kodu ve özel adlar atılır. "MECE322 kaç AKTS?" ile
    "ENG201 kaç AKTS?" aynı biçimdir; ikisini birden önermek seçenek sunmaz. Sıra sayıları
    ("1. yarıyıl", "3. sınıf") kalır: başka bir dönemi soran kalıp başka bir seçenektir."""
    return " ".join(
        word.lower()
        for word in question.split()
        if not (word[0].isupper() or _CODE_LIKE.search(word))
    )


def _distinct(documents: list[Document]) -> list[Document]:
    """Aynı yanıta götüren kalıplardan yalnızca en üstteki kalır."""
    distinct: dict[str, Document] = {}
    for document in documents:
        distinct.setdefault(document.text, document)
    return list(distinct.values())
