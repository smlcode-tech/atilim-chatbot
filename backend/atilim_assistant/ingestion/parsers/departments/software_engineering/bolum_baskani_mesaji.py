"""Bölüm Başkanının Mesajı sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container):
  - Sol sütun: fotoğraf + h3 başlıkta bölüm başkanının adı
  - Sağ sütun (col-lg-6): mesaj paragrafları
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
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

    doc = _doc(source, "mesaj", source.title, full_text)

    answers = [
        _answer(
            source,
            [
                f"{source.unit} bölüm başkanının mesajı nedir?",
                "Bölüm başkanı öğrencilere ne diyor?",
                f"{chair_name} öğrencilere mesajı",
                "Bölüm başkanından mesaj",
            ],
            "\n\n".join(paragraphs),
        )
    ]
    if chair_name:
        answers.append(
            _answer(
                source,
                [
                    f"{source.unit} bölüm başkanı kim?",
                    # Kısa kalıp şarttır: yoksa "Bölüm başkanı kim?" eşit puanla mesaj
                    # yanıtının "Bölüm başkanından mesaj" kalıbına gider.
                    "Bölüm başkanı kim?",
                    "Bölüm başkanının adı nedir?",
                ],
                f"{source.unit} Bölüm Başkanı: **{chair_name}**",
            )
        )

    return SourceContent(documents=[doc], prepared_answers=answers)


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
