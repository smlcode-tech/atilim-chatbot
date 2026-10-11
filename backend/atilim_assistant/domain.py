"""Katmanlar arasında taşınan çekirdek veri tipleri."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Document:
    """İndekslenen ve bağlam olarak modele verilen en küçük bilgi birimi."""

    id: str
    source_id: str
    source_title: str
    url: str
    unit: str
    category: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class Source:
    """Siteden alınan tek bir sayfa ve onu belgelere çeviren ayrıştırıcı."""

    id: str
    title: str
    url: str
    unit: str
    category: str
    parser: Callable[[str, "Source"], list[Document]]


@dataclass(frozen=True, slots=True)
class Citation:
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class Answer:
    text: str
    citations: list[Citation]
