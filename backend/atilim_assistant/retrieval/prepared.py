"""Hazır yanıtların kalıcı deposu ve kullanıcı sorusuyla eşleştirilmesi.

Hazır yanıtlar model sağlayıcıya ulaşılamadığında (kota, ağ, zaman aşımı) devreye girer;
bu yüzden eşleştirme hiçbir dış servise değil, yalnızca yerel sözcük karşılaştırmasına dayanır.
"""

import json
import math
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from atilim_assistant.domain import PreparedAnswer
from atilim_assistant.text import FILLER_WORDS, stem, tokenize

# Sorunun içerik sözcüklerinin (ağırlıkça) en az bu kadarı bir soru kalıbında geçmelidir.
# Daha düşük eşik, sorunun asıl konusunu karşılamayan yanıtların verilmesine yol açar.
_MIN_COVERAGE = 0.75


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

        best_score, best_answer = (0.0, 0.0), None
        for answer, patterns in zip(self._answers, self._patterns):
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


def _rarity(frequency: int, total: int) -> float:
    return math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
