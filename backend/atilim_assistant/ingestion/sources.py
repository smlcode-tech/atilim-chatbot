"""Asistanın bilgi kapsamı: indekslenen sayfaların kataloğu.

Kapsamı genişletmek için buraya yeni bir Source eklenir; sayfa yapısı mevcut
ayrıştırıcılardan birine uymuyorsa `parsers/` altına yeni bir ayrıştırıcı yazılır.
"""

from atilim_assistant.domain import Source
from atilim_assistant.ingestion.parsers.departments.software_engineering import (
    academic_staff,
    bolum_baskani_mesaji,
    department_intro,
    dersler,
    egitim_amaclari,
    endustri_danisma_kurulu,
    idari_personel,
    komiteler,
    mufredat,
    ogrenci_danisma_kurulu,
    program_ciktilari,
    sikca_sorulan_sorular,
)

_SE = "Atılım Üniversitesi Yazılım Mühendisliği Bölümü"

SOURCES: tuple[Source, ...] = (
    Source(
        id="se-tanitim",
        title="Yazılım Mühendisliği Bölümü — Tanıtım",
        url="https://www.atilim.edu.tr/tr/se",
        unit=_SE,
        category="bolum-tanitim",
        parser=department_intro.parse,
    ),
    Source(
        id="se-bolum-baskani-mesaji",
        title="Yazılım Mühendisliği Bölümü — Bölüm Başkanının Mesajı",
        url="https://www.atilim.edu.tr/tr/se/page/61/bolum-baskaninin-mesaji",
        unit=_SE,
        category="bolum-tanitim",
        parser=bolum_baskani_mesaji.parse,
    ),
    Source(
        id="se-egitim-amaclari",
        title="Yazılım Mühendisliği Bölümü — Eğitim Amaçları",
        url="https://www.atilim.edu.tr/tr/se/page/3445/egitim-amaclari",
        unit=_SE,
        category="bolum-tanitim",
        parser=egitim_amaclari.parse,
    ),
    Source(
        id="se-program-ciktilari",
        title="Yazılım Mühendisliği Bölümü — Program Çıktıları",
        url="https://www.atilim.edu.tr/tr/se/page/3446/program-ciktilari",
        unit=_SE,
        category="bolum-tanitim",
        parser=program_ciktilari.parse,
    ),
    Source(
        id="se-endustri-danisma-kurulu",
        title="Yazılım Mühendisliği Bölümü — Endüstri Danışma Kurulu",
        url="https://www.atilim.edu.tr/tr/se/page/3443/endustri-danisma-kurulu",
        unit=_SE,
        category="bolum-tanitim",
        parser=endustri_danisma_kurulu.parse,
    ),
    Source(
        id="se-ogrenci-danisma-kurulu",
        title="Yazılım Mühendisliği Bölümü — Öğrenci Danışma Kurulu",
        url="https://www.atilim.edu.tr/tr/se/page/3444/ogrenci-danisma-kurulu",
        unit=_SE,
        category="bolum-tanitim",
        parser=ogrenci_danisma_kurulu.parse,
    ),
    Source(
        id="se-sikca-sorulan-sorular",
        title="Yazılım Mühendisliği Bölümü — Sıkça Sorulan Sorular",
        url="https://www.atilim.edu.tr/tr/se/page/4704/sikca-sorulan-sorular",
        unit=_SE,
        category="bolum-tanitim",
        parser=sikca_sorulan_sorular.parse,
    ),
    Source(
        id="se-komiteler",
        title="Yazılım Mühendisliği Bölümü — Komiteler",
        url="https://www.atilim.edu.tr/tr/se/page/6582/komiteler",
        unit=_SE,
        category="bolum-tanitim",
        parser=komiteler.parse,
    ),
    Source(
        id="se-akademik-personel",
        title="Yazılım Mühendisliği Bölümü — Akademik Personel",
        url="https://www.atilim.edu.tr/tr/se/page/2286/akademik-personel",
        unit=_SE,
        category="akademik-personel",
        parser=academic_staff.parse,
    ),
    Source(
        id="se-mufredat",
        title="Yazılım Mühendisliği Bölümü — Müfredat",
        url="https://www.atilim.edu.tr/tr/se/page/2284/mufredat",
        unit=_SE,
        category="lisans-programi",
        parser=mufredat.parse,
    ),
    Source(
        id="se-dersler",
        title="Yazılım Mühendisliği Bölümü — Dersler",
        url="https://www.atilim.edu.tr/tr/se/page/2285/dersler",
        unit=_SE,
        category="lisans-programi",
        parser=dersler.parse,
    ),
    Source(
        id="se-idari-personel",
        title="Yazılım Mühendisliği Bölümü — İdari Personel",
        url="https://www.atilim.edu.tr/tr/se/page/2287/idari-personel",
        unit=_SE,
        category="idari-personel",
        parser=idari_personel.parse,
    ),
)


def get_source(source_id: str) -> Source:
    for source in SOURCES:
        if source.id == source_id:
            return source
    known = ", ".join(source.id for source in SOURCES)
    raise KeyError(f"Bilinmeyen kaynak: {source_id}. Tanımlı kaynaklar: {known}")
