"""Bölüm tanıtım ana sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı:
- `section.site_landing_container` içindeki uzun bölüm tanıtım paragrafı
- `h3.colorBlue` başlıklı Misyon ve Vizyon kutuları
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import PreparedAnswer, Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    """Tanıtım ile misyon-vizyon iki ayrı belge olur: farklı sorulara yanıt verirler ve
    uzun tanıtım metni misyon sorusunda bağlamı gereksiz yere doldururdu."""
    soup = BeautifulSoup(html, "html.parser")

    intro = _intro_text(soup)
    mission = _section_text(soup, "Misyon")
    vision = _section_text(soup, "Vizyon")

    if not intro:
        raise ValueError(f"{source.url} sayfasında bölüm tanıtım metni bulunamadı.")

    documents = [
        doc_for(source, "tanitim", "Yazılım Mühendisliği Bölümü — Tanıtım", intro),
        doc_for(source, "misyon-vizyon", "Yazılım Mühendisliği Bölümü — Misyon ve Vizyon",
             f"Misyon: {mission}\n\nVizyon: {vision}"),
    ]

    answers = _prepared_answers(source, intro, mission, vision)

    return SourceContent(documents=documents, prepared_answers=answers)


# ---------------------------------------------------------------------------
# Sayfa ayrıştırma yardımcıları
# ---------------------------------------------------------------------------

def _intro_text(soup: BeautifulSoup) -> str:
    """Giriş bölümündeki tanıtım paragrafı; menü bağlantıları metne karışmasın diye atılır."""
    landing = soup.find("section", class_="site_landing_container")
    if not landing:
        return ""
    # Nav linkleri çıkar; kalan metin = bölüm tanıtım paragrafı
    for nav in landing.select("ul, li, a"):
        nav.decompose()
    return collapse_whitespace(landing.get_text(" "))


def _sentences(text: str, *phrases: str) -> str:
    """Metindeki, ifadelerden birini içeren cümleler, sırasıyla; hiçbiri yoksa boş.

    Tanıtım paragrafı tek bir metin olarak gelir; belirli bir konuyu soran soruya paragrafın
    tamamını değil yalnızca ilgili cümleleri vermek için kullanılır.
    """
    picked = [
        sentence.strip().rstrip(".")
        for sentence in text.split(". ")
        if any(phrase in sentence for phrase in phrases)
    ]
    return " ".join(f"{sentence}." for sentence in picked)


def _section_text(soup: BeautifulSoup, heading: str) -> str:
    """Başlığı `heading` olan kutunun metni, başlığın kendisi olmadan; bulunamazsa boş."""
    for h3 in soup.find_all("h3", class_="colorBlue"):
        if heading.lower() in h3.get_text().lower():
            parent = h3.parent
            h3.decompose()
            return collapse_whitespace(parent.get_text(" "))
    return ""


def _prepared_answers(
    source: Source, intro: str, mission: str, vision: str
) -> list[PreparedAnswer]:
    """Tanıtım sayfasının hazır yanıtları.

    Akreditasyon, mezun iş olanakları ve lisansüstü programlar yanıtları tanıtım paragrafındaki
    ilgili cümlelerden kurulur; sayfadaki bilgi (ör. MÜDEK akreditasyon tarihi) değişince yanıt
    da sonraki ingest'te kendiliğinden güncellenir. Cümle bulunamazsa o yanıt üretilmez: eskimiş
    bir metin vermektense soru modele gider.
    """
    unit = source.unit
    answers = [
        answer_for(
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
        answer_for(
            source,
            [
                f"{unit} misyonu nedir?",
                "Bölümün misyon ifadesi nedir?",
                "Yazılım mühendisliği bölümünün amacı ne?",
                "Bölümün görevi, misyonu ne?",
            ],
            f"**{unit} Misyonu:** {mission}",
        ),
        answer_for(
            source,
            [
                f"{unit} vizyonu nedir?",
                "Bölümün vizyon ifadesi nedir?",
                "Yazılım mühendisliği bölümünün hedefi ne?",
                "Bölüm gelecekte ne olmayı hedefliyor?",
            ],
            f"**{unit} Vizyonu:** {vision}",
        ),
    ]

    # Soru kalıpları → yanıtın kurulacağı cümlelerin ifadeleri. "Bölümümüz mezunları" yalın
    # "mezunları" değildir: o, akreditasyon cümlesindeki "mezunlarımız"ı da yakalardı.
    topics = [
        (
            [
                "MÜDEK akreditasyonu var mı?",
                "EUR-ACE etiketi nedir?",
                "Bölüm akredite mi?",
                "Yazılım mühendisliği mezunları Avrupa'da geçerli mi?",
                "Bölümün akreditasyonu var mı, ne zamana kadar geçerli?",
                "Diploma yurt dışında tanınıyor mu?",
            ],
            ("MÜDEK", "Bu etiket sayesinde"),
        ),
        (
            [
                "Yazılım mühendisliği mezunları nerede çalışabilir?",
                "Mezun iş imkânları neler?",
                "Bölüm mezunları hangi sektörlerde iş bulabilir?",
                "Yazılım mühendisleri nerelerde iş bulur, kariyer olanakları neler?",
                "Mezunlar hangi kurum ve firmalarda çalışıyor?",
            ],
            ("Bölümümüz mezunları",),
        ),
        (
            [
                "Doktora programı var mı?",
                "Yüksek lisans programı var mı?",
                "Lisansüstü eğitim imkânı nedir?",
                "Türkiye'de yazılım mühendisliği doktorası hangi üniversitelerde var?",
                "Mezun olduktan sonra master veya doktora yapabilir miyim?",
                "Bölümde lisansüstü program var mı?",
            ],
            ("Doktora düzeyinde",),
        ),
    ]
    for questions, phrases in topics:
        text = _sentences(intro, *phrases)
        if text:
            answers.append(answer_for(source, questions, text))
    return answers
