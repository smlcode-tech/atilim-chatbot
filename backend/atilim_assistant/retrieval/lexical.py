"""Bellek içi BM25 anahtar kelime araması.

Vektör aramasının kaçırabildiği özel adlar (kişi, birim, ders kodu) için kullanılır.
"""

import math
import re
from collections import Counter

from atilim_assistant.domain import Document
from atilim_assistant.text import FILLER_WORDS, tokenize

_K1 = 1.5
_B = 0.75

_SUBJECT = re.compile(r"[a-z]{2,4}")
_COURSE_NUMBER = re.compile(r"\d{3}")


class LexicalIndex:
    def __init__(self, documents: list[Document]) -> None:
        self._documents = documents
        self._term_counts = [Counter(_terms(f"{d.title} {d.text}")) for d in documents]
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
        terms = [term for term in set(_terms(query)) if term in self._idf]
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


def _terms(text: str) -> list[str]:
    """Dolgu sözcükleri atılır: BM25 anlamı bilmez, "için" gibi bir bağlaç az belgede geçtiği
    için yüksek ağırlık alıp alakasız belgeleri öne çıkarabilir. Ders kodları hem "SE212" hem
    "SE 212" yazıldığından boşluklu yazıma birleşik terim de eklenir."""
    tokens = tokenize(text)
    terms = [token for token in tokens if token not in FILLER_WORDS]
    for subject, number in zip(tokens, tokens[1:]):
        if _SUBJECT.fullmatch(subject) and _COURSE_NUMBER.fullmatch(number):
            terms.append(subject + number)
    return terms
