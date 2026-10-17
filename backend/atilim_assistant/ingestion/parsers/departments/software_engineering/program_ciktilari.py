"""Program Çıktıları sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - Üç sütunlu tablo: PÇ kodu | açıklama | ilgili dersler
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    outcomes: list[tuple[str, str, str]] = []
    for row in container.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 3:
            continue
        code = collapse_whitespace(cells[0].get_text())
        description = collapse_whitespace(cells[1].get_text())
        courses = collapse_whitespace(cells[2].get_text())
        if code and description:
            outcomes.append((code, description, courses))

    if not outcomes:
        raise ValueError(f"{source.url} sayfasında program çıktısı tablosu bulunamadı.")

    documents: list[Document] = []

    roster_lines = [f"{source.title} ({len(outcomes)} çıktı):"]
    for code, description, _ in outcomes:
        roster_lines.append(f"- {code}: {description[:80]}{'…' if len(description) > 80 else ''}")
    documents.append(_doc(source, "liste", source.title, "\n".join(roster_lines)))

    for code, description, courses in outcomes:
        lines = [f"{code} — {source.unit} program çıktısı", f"Açıklama: {description}"]
        if courses:
            lines.append(f"İlgili dersler: {courses}")
        slug = code.lower().replace(" ", "-")
        documents.append(_doc(source, slug, code, "\n".join(lines)))

    answers: list[PreparedAnswer] = [
        _answer(
            source,
            [
                f"{source.unit} program çıktıları nelerdir?",
                "Yazılım mühendisliği program çıktıları",
                "PÇ listesi nedir?",
                "Bölüm mezunları hangi yetkinliklere sahip olur?",
                "Öğrenme çıktıları, kazanımlar neler?",
                "Mezunlar bölümden ne kazanır, hangi becerileri edinir?",
            ],
            "\n".join(roster_lines),
        )
    ]
    for code, description, courses in outcomes:
        answer_text = f"**{code}:** {description}"
        if courses:
            answer_text += f"\n\nİlgili dersler: {courses}"
        answers.append(
            _answer(
                source,
                [
                    f"{code} program çıktısı nedir?",
                    f"{code} açıklaması nedir?",
                    f"{code} nedir?",
                    *_number_questions(code),
                ],
                answer_text,
            )
        )

    return SourceContent(documents=documents, prepared_answers=answers)


def _number_questions(code: str) -> list[str]:
    """"PÇ3" → "3. program çıktısı nedir?"; harfli kodlarda ("PÇ9a") sayı tek başına yetmez."""
    number = code.removeprefix("PÇ").strip()
    if not number.isdigit():
        return []
    return [f"{number}. program çıktısı nedir?", f"{number} numaralı öğrenme çıktısı nedir?"]


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
