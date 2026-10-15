"""Hazır yanıtların kalıcı deposu ve kullanıcı sorusuyla eşleştirilmesi.

Hazır yanıtlar model sağlayıcıya ulaşılamadığında (kota, ağ, zaman aşımı) devreye girer;
bu yüzden eşleştirme hiçbir dış servise değil, yalnızca yerel sözcük karşılaştırmasına dayanır.
"""

import json
import math
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from atilim_assistant.domain import PreparedAnswer
from atilim_assistant.text import FILLER_WORDS, normalize, stem, tokenize

# Sorunun içerik sözcüklerinin (ağırlıkça) en az bu kadarı bir soru kalıbında geçmelidir.
# Daha düşük eşik, sorunun asıl konusunu karşılamayan yanıtların verilmesine yol açar.
_MIN_COVERAGE = 0.75

# "Bilgisayar mühendisliği", "Hukuk fakültesi" gibi birim adlarının niteleyicisi. Bölüm adı
# tek bir sözcükle değişir ve kapsam ölçüsünü pek etkilemez; bu yüzden ayrıca denetlenir.
_UNIT_QUALIFIER = re.compile(r"(\w+) (?:muhendislig|bolum|fakulte|program)\w*")
_UNIT_WORDS = ("muhendislig", "bolum", "fakulte", "program")
# Niteleyici karşılaştırmasında kullanılan önek uzunluğu; `stem`in 5 harfi "bilgisayar" ile
# "bilgi"yi ayırt etmez.
_QUALIFIER_PREFIX = 7


class PreparedAnswerStore:
    """Hazır yanıtları tek bir JSON dosyasında tutar."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def replace_source(self, source_id: str, answers: list[PreparedAnswer]) -> None:
        kept = [answer for answer in self.all() if answer.source_id != source_id]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(answer) for answer in kept + answers], ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    def all(self) -> list[PreparedAnswer]:
        if not self._path.exists():
            return []
        return [
            PreparedAnswer(**item) for item in json.loads(self._path.read_text(encoding="utf-8"))
        ]


class PreparedAnswerMatcher:
    def __init__(self, answers: list[PreparedAnswer]) -> None:
        self._answers = answers
        self._patterns = [[_terms(question) for question in a.questions] for a in answers]
        self._scopes = [_prefixes(" ".join([a.source_title, *a.questions])) for a in answers]

        # Az sayıda yanıtta geçen terimler (kişi adı, konu) ayırt edicidir ve daha ağır sayılır.
        answer_frequency = Counter(
            term for patterns in self._patterns for term in frozenset().union(*patterns)
        )
        total = len(answers)
        self._weights = {
            term: _rarity(frequency, total) for term, frequency in answer_frequency.items()
        }
        self._unknown_weight = _rarity(0, total)

    def match(self, question: str) -> PreparedAnswer | None:
        """Soruyu yeterince karşılayan hazır yanıtı döndürür; yoksa None."""
        terms = _terms(question)
        if not terms:
            return None

        qualifiers = _unit_qualifiers(question)
        best_score, best_answer = (0.0, 0.0), None
        for answer, patterns, scope in zip(self._answers, self._patterns, self._scopes):
            # Soru başka bir birimi adıyla soruyorsa o birimi anmayan yanıt verilmez.
            if not qualifiers <= scope:
                continue
            for pattern in patterns:
                if not terms & pattern:
                    continue
                shared = self._weight(terms & pattern)
                # Önce sorunun ne kadarının karşılandığına, eşitlikte kalıbın soruya ne kadar
                # özgü olduğuna bakılır ("Ali Yazıcı" → araştırma konuları değil, tanıtım yanıtı).
                score = (shared / self._weight(terms), shared / self._weight(pattern))
                if score > best_score:
                    best_score, best_answer = score, answer
        return best_answer if best_score[0] >= _MIN_COVERAGE else None

    def _weight(self, terms: frozenset[str]) -> float:
        return sum(self._weights.get(term, self._unknown_weight) for term in terms)


def _terms(text: str) -> frozenset[str]:
    return frozenset(stem(token) for token in tokenize(text) if token not in FILLER_WORDS)


def _prefixes(text: str) -> frozenset[str]:
    return frozenset(token[:_QUALIFIER_PREFIX] for token in tokenize(text))


def _unit_qualifiers(question: str) -> frozenset[str]:
    """Sorudaki birim adlarının niteleyicileri: "bilgisayar mühendisliği" → {"bilgisa"}."""
    return frozenset(
        word[:_QUALIFIER_PREFIX]
        for word in _UNIT_QUALIFIER.findall(normalize(question))
        if not word.startswith(_UNIT_WORDS) and word not in FILLER_WORDS
    )


def _rarity(frequency: int, total: int) -> float:
    return math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
