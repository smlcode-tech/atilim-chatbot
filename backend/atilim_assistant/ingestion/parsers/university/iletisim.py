"""Üniversitenin İletişim sayfasını belgeye ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container):
  - h2: yerleşkenin adı ("Atılım Üniversitesi - İncek Yerleşkesi")
  - "<strong>Adres</strong>: …" biçiminde etiketli paragraflar (adres, telefon, faks)
  - "<strong>Rektörlük</strong><br>adres@…" biçiminde birim e-postaları

Yanıta Google Haritalar gömme bağlantısı eklenir; arayüz bu bağlantıyı gömülü harita olarak
gösterir (bkz. `frontend/src/components/MessageList.tsx`).
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for
from atilim_assistant.text import collapse_whitespace

# Kampüsün haritası. Sayfadaki iframe'in merkezi yerleşkenin doğusuna kaymış; bu bağlantı
# yerleşkeyi ortalayan, aynı yere (place id 0x384ab208be168a84) bağlı görünümdür.
MAP_EMBED_URL = (
    "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d24517.32190583741"
    "!2d32.686949274316405!3d39.81450029999999!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1"
    "!3m3!1m2!1s0x14d3407d8c118cc7%3A0x384ab208be168a84"
    "!2zQXTEsWzEsW0gw5xuaXZlcnNpdGVzaQ!5e0!3m2!1str!2str!4v1792716653747!5m2!1str!2str"
)


def parse(html: str, source: Source) -> SourceContent:
    """Adres, telefon ve e-postalar tek belge olur. Hazır yanıtlar ikiye ayrılır: konum
    sorusu adresi ve haritayı, iletişim sorusu telefon ve e-postaları da alır. Adres
    bulunamazsa sayfa yapısı değişmiştir; eski veri korunsun diye hata verilir."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    heading = container.find("h2")
    campus = collapse_whitespace(heading.get_text()) if heading else source.unit

    fields: dict[str, str] = {}
    emails: list[str] = []
    for p in container.find_all("p"):
        label = p.find("strong")
        if not label:
            continue
        name = collapse_whitespace(label.get_text())
        rest = collapse_whitespace(p.get_text().replace(label.get_text(), "", 1))
        if rest.startswith(":"):
            fields[name] = rest.lstrip(": ")
        elif "@" in rest:
            emails.append(f"{name}: {rest}")

    address = fields.get("Adres")
    if not address:
        raise ValueError(f"{source.url} sayfasında adres bulunamadı.")

    location = f"**{campus}**\n\nAdres: {address}\n\n[Haritada göster]({MAP_EMBED_URL})"
    contact_lines = [f"{name}: {value}" for name, value in fields.items() if name != "Adres"]
    contact = "\n\n".join([location, *contact_lines, *emails])

    doc = doc_for(source, "iletisim", source.title, contact)
    answers = [
        answer_for(
            source,
            [
                "Atılım Üniversitesi nerede?",
                "Okulun adresi nedir?",
                "Atılım Üniversitesi'nin adresi nedir?",
                "Üniversitenin konumu, adresi",
                "Kampüs nerede, hangi semtte?",
                "Okul haritada nerede, konum at",
                "Atılım İncek yerleşkesi nerede?",
            ],
            location,
        ),
        answer_for(
            source,
            [
                "Atılım Üniversitesi iletişim bilgileri neler?",
                "Üniversitenin telefon numarası nedir?",
                "Okulun telefon numarası nedir?",
                "Okulu nasıl ararım, santral numarası",
                "Rektörlük e-posta adresi nedir?",
                "Üniversitenin faks numarası",
            ],
            contact,
        ),
    ]
    return SourceContent(documents=[doc], prepared_answers=answers)
