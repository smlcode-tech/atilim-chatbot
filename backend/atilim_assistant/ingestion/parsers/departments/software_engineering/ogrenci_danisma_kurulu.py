"""Öğrenci Danışma Kurulu sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - Tek sütunlu tablo: Öğrenci Ad Soyad
  - İlk satır başlık satırıdır.
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    students: list[str] = []
    for row in container.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 1:
            continue
        name = collapse_whitespace(cells[0].get_text())
        if name and name != "Öğrenci Ad Soyad":
            students.append(name)

    if not students:
        raise ValueError(f"{source.url} sayfasında öğrenci danışma kurulu tablosu bulunamadı.")

    roster_lines = [f"{source.title} ({len(students)} öğrenci):"]
    for name in students:
        roster_lines.append(f"- {name}")

    doc = _doc(source, "liste", source.title, "\n".join(roster_lines))

    answers = [
        _answer(
            source,
            [
                f"{source.unit} öğrenci danışma kurulu kimlerden oluşuyor?",
                "Öğrenci danışma kurulu üyeleri kimler?",
                "Yazılım mühendisliği öğrenci temsilcileri kimler?",
            ],
            "\n".join(roster_lines),
        )
    ]

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
