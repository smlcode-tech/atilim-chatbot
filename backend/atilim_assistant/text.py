"""Türkçe metin için arama odaklı normalleştirme."""

import re
import unicodedata

_TURKISH_I = str.maketrans("İIı", "iii")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Küçük harfe çevirir, Türkçe harfleri ASCII karşılığına indirger, noktalamayı boşluk yapar."""
    folded = unicodedata.normalize("NFKD", text.translate(_TURKISH_I))
    ascii_text = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return _NON_ALNUM.sub(" ", ascii_text.lower()).strip()


def tokenize(text: str) -> list[str]:
    return [token for token in normalize(text).split() if len(token) >= 2]


def stem(token: str) -> str:
    """Çekim eklerini kabaca yok sayar: Türkçede sözcüğün ilk 5 harfi köke yakın sonuç verir."""
    return token[:5]


def slugify(text: str) -> str:
    return normalize(text).replace(" ", "-")


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()
