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
class PreparedAnswer:
    """Sayfa verisinden şablonla üretilen, model olmadan verilebilen hazır yanıt.

    `questions`, yanıtın karşıladığı örnek soru kalıplarıdır; kullanıcının sorusu bunlarla eşleştirilir.
    """

    source_id: str
    source_title: str
    url: str
    questions: list[str]
    answer: str


@dataclass(frozen=True, slots=True)
class SourceContent:
    """Bir kaynak sayfanın ayrıştırılmış içeriği."""

    documents: list[Document]
    prepared_answers: list[PreparedAnswer]


@dataclass(frozen=True, slots=True)
class Source:
    """Siteden alınan tek bir sayfa ve onu içeriğe çeviren ayrıştırıcı."""

    id: str
    title: str
    url: str
    unit: str
    category: str
    parser: Callable[[str, "Source"], SourceContent]


@dataclass(frozen=True, slots=True)
class Citation:
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class Answer:
    """`prepared`: yanıt model tarafından üretilmedi, hazır yanıtlardan verildi."""

    text: str
    citations: list[Citation]
    prepared: bool = False
