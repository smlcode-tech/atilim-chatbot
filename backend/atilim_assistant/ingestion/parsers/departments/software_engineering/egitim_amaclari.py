"""Eğitim Amaçları sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - <strong> ile kalın yazılmış başlık
  - Giriş paragrafı
  - <ol> listesiyle üç eğitim amacı
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    intro = ""
    for p in container.find_all("p"):
        text = collapse_whitespace(p.get_text())
        if text and not p.find("strong"):
            intro = text
            break

    goals = [collapse_whitespace(li.get_text()) for li in container.find_all("li") if collapse_whitespace(li.get_text())]

    if not goals:
        raise ValueError(f"{source.url} sayfasında eğitim amaçları listesi bulunamadı.")

    lines = [source.title]
    if intro:
        lines.append(intro)
    for i, goal in enumerate(goals, 1):
        lines.append(f"{i}. {goal}")

    doc = _doc(source, "egitim-amaclari", source.title, "\n".join(lines))

    goals_text = (f"{intro}\n" if intro else "") + "\n".join(f"{i}. {g}" for i, g in enumerate(goals, 1))
    answers = [
        _answer(
            source,
            [
                f"{source.unit} eğitim amaçları nelerdir?",
                "Program eğitim amaçları neler?",
                "Yazılım mühendisliği bölümünün hedefleri nelerdir?",
                "Mezunlar hangi alanlarda çalışacak şekilde yetiştirilir?",
            ],
            goals_text,
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
