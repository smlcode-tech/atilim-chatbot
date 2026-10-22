"""Öğrenci Danışma Kurulu sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - Tek sütunlu tablo: Öğrenci Ad Soyad
  - İlk satır başlık satırıdır.
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    """Öğrenci listesi tek belge ve tek hazır yanıt olur; kurul küçüktür ve hep bütün olarak sorulur."""
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

    doc = doc_for(source, "liste", source.title, "\n".join(roster_lines))

    answers = [
        answer_for(
            source,
            [
                f"{source.unit} öğrenci danışma kurulu kimlerden oluşuyor?",
                "Öğrenci danışma kurulu üyeleri kimler?",
                "Yazılım mühendisliği öğrenci temsilcileri kimler?",
                "Bölüm öğrenci temsilcisi kim?",
                "Öğrenci danışma kurulunda kimler var?",
            ],
            "\n".join(roster_lines),
        )
    ]

    return SourceContent(documents=[doc], prepared_answers=answers)
