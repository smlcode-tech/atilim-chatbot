"""Asistanın bilgi kapsamı: indekslenen sayfaların kataloğu.

Kapsamı genişletmek için buraya yeni bir Source eklenir; sayfa yapısı mevcut
ayrıştırıcılardan birine uymuyorsa `parsers/` altına yeni bir ayrıştırıcı yazılır.
"""

from atilim_assistant.domain import Source
from atilim_assistant.ingestion.parsers import academic_staff

SOURCES: tuple[Source, ...] = (
    Source(
        id="se-akademik-personel",
        title="Yazılım Mühendisliği Bölümü — Akademik Personel",
        url="https://www.atilim.edu.tr/tr/se/page/2286/akademik-personel",
        unit="Atılım Üniversitesi Yazılım Mühendisliği Bölümü",
        category="akademik-personel",
        parser=academic_staff.parse,
    ),
)


def get_source(source_id: str) -> Source:
    for source in SOURCES:
        if source.id == source_id:
            return source
    known = ", ".join(source.id for source in SOURCES)
    raise KeyError(f"Bilinmeyen kaynak: {source_id}. Tanımlı kaynaklar: {known}")
