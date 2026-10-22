"""Bölüm Başkanının Mesajı sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container):
  - Sol sütun: fotoğraf + h3 başlıkta bölüm başkanının adı
  - Sağ sütun (col-lg-6): mesaj paragrafları
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    """Mesaj tek belge olur. Hazır yanıtlar ikiye ayrılır: "mesajı ne?" sorusu mesajın
    tamamını, "bölüm başkanı kim?" sorusu yalnızca adı alır; uzun mesaj kısa soruya yanıt olmaz.
    Ad bulunamazsa yalnızca mesaj yanıtı üretilir."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    caption = container.find(class_="imgCaption-content")
    chair_name = collapse_whitespace(caption.find("h3").get_text()) if caption and caption.find("h3") else ""

    text_col = container.find("div", class_=lambda c: c and "col-lg-6" in c and "col-md-6" in c)
    paragraphs = []
    if text_col:
        for p in text_col.find_all("p"):
            text = collapse_whitespace(p.get_text())
            if text:
                paragraphs.append(text)

    if not paragraphs:
        raise ValueError(f"{source.url} sayfasında mesaj metni bulunamadı.")

    heading = f"{chair_name} — {source.unit} Bölüm Başkanı" if chair_name else source.title
    full_text = "\n\n".join([heading, *paragraphs])

    doc = doc_for(source, "mesaj", source.title, full_text)

    answers = [
        answer_for(
            source,
            [
                f"{source.unit} bölüm başkanının mesajı nedir?",
                "Bölüm başkanı öğrencilere ne diyor?",
                f"{chair_name} öğrencilere mesajı",
                "Bölüm başkanından mesaj",
                "Bölüm başkanının öğrencilere mesajı, konuşması",
            ],
            "\n\n".join(paragraphs),
        )
    ]
    if chair_name:
        answers.append(
            answer_for(
                source,
                [
                    f"{source.unit} bölüm başkanı kim?",
                    # Kısa kalıp şarttır: yoksa "Bölüm başkanı kim?" eşit puanla mesaj
                    # yanıtının "Bölüm başkanından mesaj" kalıbına gider.
                    "Bölüm başkanı kim?",
                    "Bölüm başkanının adı nedir?",
                    "Bölümün başında kim var?",
                    "Bölüm şefi kim?",
                ],
                f"{source.unit} Bölüm Başkanı: **{chair_name}**",
            )
        )

    return SourceContent(documents=[doc], prepared_answers=answers)
