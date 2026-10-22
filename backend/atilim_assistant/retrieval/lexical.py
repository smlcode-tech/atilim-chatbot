"""Bellek içi BM25 anahtar kelime araması.

Vektör aramasının kaçırabildiği özel adlar (kişi, birim, ders kodu) için kullanılır.

Bellekte hesaplanır, ayrı bir arama servisi gerekmez. Her sorgu tüm belgeleri tarar; bu,
bugünkü boyutta (birkaç yüz sayfa parçası, birkaç bin soru kalıbı) yeterince hızlıdır. Kapsam
tüm siteye genişlediğinde yeniden değerlendirilmelidir.
"""

import math
import re
from collections import Counter

from atilim_assistant.domain import Document
from atilim_assistant.text import FILLER_WORDS, canonicalize, tokenize

# BM25'in standart parametreleri: `_K1` aynı terimin tekrarının puana katkısını doyurur,
# `_B` uzun belgelerin yalnızca uzun oldukları için öne çıkmasını engeller.
_K1 = 1.5
_B = 0.75

# Boşluklu yazılmış ders kodunun parçaları ("se 212"): harf öneki ve üç haneli numara.
_SUBJECT = re.compile(r"[a-z]{2,4}")
_COURSE_NUMBER = re.compile(r"\d{3}")
# Birleşik ders kodu terimi ("se212", "math151a").
_COURSE_CODE = re.compile(r"[a-z]{2,5}\d{3}[a-z]?")


class LexicalIndex:
    """Belgelerin terim sayıları ve terim ağırlıkları (IDF), kurulurken bir kez hesaplanır.

    İndeks değişmez; yeni belgeler için yeniden kurulur. `HybridRetriever` iki tane kurar:
    sayfa belgeleri için ve yalnızca soru kalıplarının sözcükleri için.
    """

    def __init__(self, documents: list[Document]) -> None:
        self._documents = documents
        self._term_counts = [Counter(_terms(f"{d.title} {d.text}")) for d in documents]
        self._lengths = [sum(counts.values()) for counts in self._term_counts]
        self._average_length = sum(self._lengths) / max(len(documents), 1)

        document_frequency = Counter(term for counts in self._term_counts for term in counts)
        # Belgelerde geçen ders kodları; yanlış yazılmış kodları düzeltmek için kullanılır.
        self.course_codes = frozenset(
            term for term in document_frequency if _COURSE_CODE.fullmatch(term)
        )
        total = len(documents)
        # Az belgede geçen terim ayırt edicidir, çok belgede geçen terim (ör. "bölüm") değildir.
        # `1 +` ile her belgede geçen terimin ağırlığı negatife düşmez.
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
        """Tek bir terimin bir belgedeki BM25 katkısı (standart formül)."""
        frequency = counts[term]
        if not frequency:
            return 0.0
        normalization = 1 - _B + _B * length / self._average_length
        return self._idf[term] * frequency * (_K1 + 1) / (frequency + _K1 * normalization)


def _terms(text: str) -> list[str]:
    """Dolgu sözcükleri atılır: BM25 anlamı bilmez, "için" gibi bir bağlaç az belgede geçtiği
    için yüksek ağırlık alıp alakasız belgeleri öne çıkarabilir. Ders kodları hem "SE212" hem
    "SE 212" yazıldığından boşluklu yazıma birleşik terim de eklenir. Eş anlamlılar kanonik
    biçime indirilir ("ön şart" sorusu "ön koşul" geçen belgeyi bulur)."""
    tokens = tokenize(canonicalize(text))
    terms = [token for token in tokens if token not in FILLER_WORDS]
    for subject, number in zip(tokens, tokens[1:]):
        if _SUBJECT.fullmatch(subject) and _COURSE_NUMBER.fullmatch(number):
            terms.append(subject + number)
    return terms
