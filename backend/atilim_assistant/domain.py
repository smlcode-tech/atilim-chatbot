"""Katmanlar arasında taşınan çekirdek veri tipleri.

Hiçbir dış pakete (FastAPI, pymongo, openai, chromadb) bağlı değildir; her katman bu tipleri
konuşur ve kendi dış biçimine (HTTP gövdesi, Mongo belgesi, Chroma üst verisi) kendisi çevirir.
Tipler değişmezdir (`frozen`): katmanlar arasında paylaşılan bir nesne yolda değiştirilemez.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class Document:
    """İndekslenen ve bağlam olarak modele verilen en küçük bilgi birimi."""

    id: str
    # Belgenin geldiği kaynak; yeniden indekslemede o kaynağın belgeleri birlikte değişir.
    source_id: str
    # Kaynak sayfanın adı ve adresi; yanıtta kaynak olarak gösterilir.
    source_title: str
    url: str
    # Belgenin ait olduğu birim (ör. bölüm) ve konu kategorisi.
    unit: str
    category: str
    # Sayfa içindeki bölümün başlığı; soru kalıbı belgelerinde kalıbın kendisidir.
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
    """Bir kaynak sayfanın ayrıştırılmış içeriği: ayrıştırıcının çıktısı, ingest'in girdisi.

    Aynı sayfa üç biçimde kullanılır: metin araması için belgeler, model kesintisi için hazır
    yanıtlar, liste ve süzme soruları için yapılandırılmış kayıtlar.
    """

    documents: list[Document]
    prepared_answers: list[PreparedAnswer]
    # Yapılandırılmış kayıtlar (ders, personel); katalog araçları bunları sorgular.
    # Anahtar kayıt türüdür ("courses", "staff"), değer satırlardır.
    records: dict[str, list[dict]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Source:
    """Siteden alınan tek bir sayfa ve onu içeriğe çeviren ayrıştırıcı."""

    id: str
    title: str
    url: str
    unit: str
    category: str
    # Sayfanın HTML'ini içeriğe çevirir; her sayfa yapısı farklı olduğu için kaynağa özgüdür.
    parser: Callable[[str, "Source"], SourceContent]
    # Verilirse sayfa siteden çekilmez, bu dosyadan okunur.
    local_content_path: Path | None = None


@dataclass(frozen=True, slots=True)
class Citation:
    """Yanıtın dayandığı sayfa: adı ve adresi."""

    title: str
    url: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Modelin çağırmak istediği araç; `arguments` JSON metnidir."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class Completion:
    """Modelin bir turu: ya yanıt metni ya da çağrılacak araçlar."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Answer:
    """`ChatService`'in bir soruya verdiği yanıt; API bunu `ChatResponse`'a çevirir.

    `prepared`: yanıt model tarafından üretilmedi, hazır yanıtlardan verildi.
    `suggestions`: soru yanıtlanamadığında kullanıcıya seçenek olarak sunulan yakın sorular."""

    text: str
    citations: list[Citation]
    prepared: bool = False
    suggestions: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class User:
    """Google ile giriş yapmış kullanıcı. `id` uygulamanın kendi kimliğidir, Google'ınki değil."""

    id: str
    email: str
    name: str


@dataclass(frozen=True, slots=True)
class Turn:
    """Bir konuşmadaki tek bir söz: kullanıcının sorusu ya da asistanın yanıtı."""

    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # Asistan yanıtının kaynak sayfaları; konuşma yeniden açıldığında da gösterilir.
    sources: list["Citation"] = field(default_factory=list)
    # Asistan soruyu yanıtlayamadığında sunduğu, yanıtı olan yakın sorular.
    suggestions: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    """Yan bardaki geçmiş listesinin bir satırı; turları taşımaz."""

    id: str
    title: str
    updated_at: datetime
