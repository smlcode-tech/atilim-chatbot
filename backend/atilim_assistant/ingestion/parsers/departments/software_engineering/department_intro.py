"""Bölüm tanıtım ana sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı:
- `section.site_landing_container` içindeki uzun bölüm tanıtım paragrafı
- `h3.colorBlue` başlıklı Misyon ve Vizyon kutuları
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")

    intro = _intro_text(soup)
    mission = _section_text(soup, "Misyon")
    vision = _section_text(soup, "Vizyon")

    if not intro:
        raise ValueError(f"{source.url} sayfasında bölüm tanıtım metni bulunamadı.")

    documents = [
        _doc(source, "tanitim", "Yazılım Mühendisliği Bölümü — Tanıtım", intro),
        _doc(source, "misyon-vizyon", "Yazılım Mühendisliği Bölümü — Misyon ve Vizyon",
             f"Misyon: {mission}\n\nVizyon: {vision}"),
    ]

    answers = _prepared_answers(source, intro, mission, vision)

    return SourceContent(documents=documents, prepared_answers=answers)


# ---------------------------------------------------------------------------
# Sayfa ayrıştırma yardımcıları
# ---------------------------------------------------------------------------

def _intro_text(soup: BeautifulSoup) -> str:
    landing = soup.find("section", class_="site_landing_container")
    if not landing:
        return ""
    # Nav linkleri çıkar; kalan metin = bölüm tanıtım paragrafı
    for nav in landing.select("ul, li, a"):
        nav.decompose()
    return collapse_whitespace(landing.get_text(" "))


def _section_text(soup: BeautifulSoup, heading: str) -> str:
    for h3 in soup.find_all("h3", class_="colorBlue"):
        if heading.lower() in h3.get_text().lower():
            parent = h3.parent
            h3.decompose()
            return collapse_whitespace(parent.get_text(" "))
    return ""


# ---------------------------------------------------------------------------
# Belge ve hazır yanıt fabrikaları
# ---------------------------------------------------------------------------

def _doc(source: Source, local_id: str, title: str, text: str) -> Document:
    return Document(
        id=f"{source.id}:{local_id}",
        source_id=source.id,
        source_title=source.title,
        url=source.url,
        unit=source.unit,
        category=source.category,
        title=title,
        text=text,
    )


def _answer(source: Source, questions: list[str], answer: str) -> PreparedAnswer:
    return PreparedAnswer(
        source_id=source.id,
        source_title=source.title,
        url=source.url,
        questions=questions,
        answer=answer,
    )


def _prepared_answers(
    source: Source, intro: str, mission: str, vision: str
) -> list[PreparedAnswer]:
    unit = source.unit
    return [
        _answer(
            source,
            [
                f"{unit} hakkında bilgi verir misin?",
                f"{unit} nedir?",
                "Yazılım mühendisliği bölümü ne zaman kuruldu?",
                "Yazılım mühendisliği bölümünü tanıtır mısın?",
                "SE bölümü hakkında genel bilgi",
                "Atılım yazılım mühendisliği bölümü",
                "Yazılım mühendisliği bölümünü anlatır mısın?",
                "Bölüm ne zaman açıldı, kaç yıllık?",
            ],
            intro,
        ),
        _answer(
            source,
            [
                f"{unit} misyonu nedir?",
                "Bölümün misyon ifadesi nedir?",
                "Yazılım mühendisliği bölümünün amacı ne?",
                "Bölümün görevi, misyonu ne?",
            ],
            f"**{unit} Misyonu:** {mission}",
        ),
        _answer(
            source,
            [
                f"{unit} vizyonu nedir?",
                "Bölümün vizyon ifadesi nedir?",
                "Yazılım mühendisliği bölümünün hedefi ne?",
                "Bölüm gelecekte ne olmayı hedefliyor?",
            ],
            f"**{unit} Vizyonu:** {vision}",
        ),
        _answer(
            source,
            [
                "MÜDEK akreditasyonu var mı?",
                "EUR-ACE etiketi nedir?",
                "Bölüm akredite mi?",
                "Yazılım mühendisliği mezunları Avrupa'da geçerli mi?",
                "Bölümün akreditasyonu var mı, ne zamana kadar geçerli?",
                "Diploma yurt dışında tanınıyor mu?",
            ],
            (
                f"{unit}, MÜDEK tarafından 30 Eylül 2030 tarihine kadar akredite edilmiş "
                "ve Avrupa'da geçerli EUR-ACE etiketi almıştır. "
                "Bu sayede mezunlar AB ülkelerinde lisansüstü programlara kabul ve "
                "çalışma ortamlarına girmede avantaj elde etmektedir."
            ),
        ),
        _answer(
            source,
            [
                "Yazılım mühendisliği mezunları nerede çalışabilir?",
                "Mezun iş imkânları neler?",
                "Bölüm mezunları hangi sektörlerde iş bulabilir?",
                "Yazılım mühendisleri nerelerde iş bulur, kariyer olanakları neler?",
                "Mezunlar hangi kurum ve firmalarda çalışıyor?",
            ],
            (
                f"{unit} mezunları; yazılım ve AR-GE firmalarında (Teknoparklarda), "
                "bankalar, sağlık kurumları, kamu bilgi işlem merkezleri, Telekom firmaları, "
                "TÜİK, SPK, BDDK, EPDK ve üniversiteler gibi ulusal/uluslararası kurumlarda "
                "ile TÜBİTAK gibi araştırma kurumlarında çalışabilmektedir."
            ),
        ),
        _answer(
            source,
            [
                "Doktora programı var mı?",
                "Yüksek lisans programı var mı?",
                "Lisansüstü eğitim imkânı nedir?",
                "Türkiye'de yazılım mühendisliği doktorası hangi üniversitelerde var?",
                "Mezun olduktan sonra master veya doktora yapabilir miyim?",
                "Bölümde lisansüstü program var mı?",
            ],
            (
                f"{unit}, Lisans, Yüksek Lisans ve Doktora düzeyinde eğitim vermektedir. "
                "Üniversite, Yazılım Mühendisliği alanında Türkiye'de Doktora düzeyinde "
                "eğitim veren iki üniversiteden biridir."
            ),
        ),
    ]
