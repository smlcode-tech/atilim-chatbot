"""Katmanlar arasında taşınan çekirdek veri tipleri."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal


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
    local_content_path: Path | None = None


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


@dataclass(frozen=True, slots=True)
class User:
    """Google ile giriş yapmış kullanıcı."""

    id: str
    email: str
    name: str


@dataclass(frozen=True, slots=True)
class Turn:
    """Bir konuşmadaki tek bir söz: kullanıcının sorusu ya da asistanın yanıtı."""

    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    """Yan bardaki geçmiş listesinin bir satırı; turları taşımaz."""

    id: str
    title: str
    updated_at: datetime
