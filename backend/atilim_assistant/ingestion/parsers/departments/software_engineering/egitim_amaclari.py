"""Eğitim Amaçları sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - <strong> ile kalın yazılmış başlık
  - Giriş paragrafı
  - <ol> listesiyle üç eğitim amacı
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    """Tek belge ve tek hazır yanıt: amaçlar kısa bir listedir, bölünmesi aramaya katkı vermez."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    # Giriş, kalın başlık taşımayan ilk paragraftır; başlık paragrafı atlanır.
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

    doc = doc_for(source, "egitim-amaclari", source.title, "\n".join(lines))

    goals_text = (f"{intro}\n" if intro else "") + "\n".join(f"{i}. {g}" for i, g in enumerate(goals, 1))
    answers = [
        answer_for(
            source,
            [
                f"{source.unit} eğitim amaçları nelerdir?",
                "Program eğitim amaçları neler?",
                "Yazılım mühendisliği bölümünün hedefleri nelerdir?",
                "Mezunlar hangi alanlarda çalışacak şekilde yetiştirilir?",
                "Bölümün eğitim hedefleri, amaçları neler?",
                "Bölüm öğrencilerini nasıl yetiştiriyor?",
            ],
            goals_text,
        )
    ]

    return SourceContent(documents=[doc], prepared_answers=answers)
