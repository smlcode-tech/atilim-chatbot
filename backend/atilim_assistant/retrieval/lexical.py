"""Bellek içi BM25 anahtar kelime araması.

Vektör aramasının kaçırabildiği özel adlar (kişi, birim, ders kodu) için kullanılır.
"""

import math
from collections import Counter

from atilim_assistant.domain import Document
from atilim_assistant.text import tokenize

_K1 = 1.5
_B = 0.75


class LexicalIndex:
    def __init__(self, documents: list[Document]) -> None:
        self._documents = documents
        self._term_counts = [Counter(tokenize(f"{d.title} {d.text}")) for d in documents]
        self._lengths = [sum(counts.values()) for counts in self._term_counts]
        self._average_length = sum(self._lengths) / max(len(documents), 1)

        document_frequency = Counter(term for counts in self._term_counts for term in counts)
        total = len(documents)
        self._idf = {
            term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(self, query: str, limit: int) -> list[Document]:
        """Sorguyla en az bir ortak terimi olan belgeleri BM25 puanına göre sıralı döndürür."""
        terms = [term for term in set(tokenize(query)) if term in self._idf]
        scored = []
        for index, counts in enumerate(self._term_counts):
            score = sum(self._term_score(term, counts, self._lengths[index]) for term in terms)
            if score > 0:
                scored.append((score, index))
        scored.sort(key=lambda item: -item[0])
        return [self._documents[index] for _, index in scored[:limit]]

    def _term_score(self, term: str, counts: Counter, length: int) -> float:
        frequency = counts[term]
        if not frequency:
            return 0.0
        normalization = 1 - _B + _B * length / self._average_length
        return self._idf[term] * frequency * (_K1 + 1) / (frequency + _K1 * normalization)
