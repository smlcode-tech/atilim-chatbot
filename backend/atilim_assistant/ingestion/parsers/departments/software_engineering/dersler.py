"""Lisans Programı "Dersler" sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div#lessons-wrapper):
  - Üç sekme: Zorunlu Dersler | Alan Seçmeli Dersler | Alan Dışı Seçmeli Dersler
  - Her sekmede div.lesson_card'lar; `data-lesson-data` JSON'u ders bilgilerini taşır.
"""

import json
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace

_TABS = {
    "required_les": "Zorunlu Dersler",
    "technical_lessons": "Alan Seçmeli Dersler",
    "general_lessons": "Alan Dışı Seçmeli Dersler",
}


@dataclass(frozen=True, slots=True)
class _Course:
    code: str
    name: str
    theory: int
    practice: int
    lab: int
    credit: float
    akts: float
    precondition: str
    content: str


@dataclass(frozen=True, slots=True)
class _Tab:
    id: str
    label: str
    courses: list[_Course] = field(default_factory=list)


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    tabs = _extract_tabs(container)
    if not any(t.courses for t in tabs):
        raise ValueError(f"{source.url} sayfasında ders kartı bulunamadı.")

    documents: list[Document] = []
    answers: list[PreparedAnswer] = []

    # Genel özet: tüm dersler
    all_lines = [f"{source.unit} Ders Listesi"]
    for tab in tabs:
        if not tab.courses:
            continue
        all_lines.append(f"\n{tab.label} ({len(tab.courses)} ders):")
        for c in tab.courses:
            all_lines.append(f"  {c.code} — {c.name} (AKTS: {c.akts})")
    full_text = "\n".join(all_lines)
    documents.append(_doc(source, "ozet", source.title, full_text))
    answers.append(
        _answer(
            source,
            [
                f"{source.unit} dersleri nelerdir?",
                "Yazılım mühendisliğinde hangi dersler var?",
                "SE bölümü ders listesi",
            ],
            full_text,
        )
    )

    # Her sekme için özet belge + hazır yanıt
    for tab in tabs:
        if not tab.courses:
            continue
        lines = [f"{source.unit} {tab.label} ({len(tab.courses)} ders):"]
        for c in tab.courses:
            lines.append(
                f"- {c.code} {c.name} | T:{c.theory} U:{c.practice} L:{c.lab} | AKTS:{c.akts}"
            )
        tab_text = "\n".join(lines)
        slug = tab.id.replace("_", "-")
        documents.append(_doc(source, slug, f"{tab.label}", tab_text))
        answers.append(
            _answer(
                source,
                [
                    f"{source.unit} {tab.label.lower()} nelerdir?",
                    f"{tab.label} listesi",
                ],
                tab_text,
            )
        )

    # Her ders için ayrı belge + hazır yanıt
    for tab in tabs:
        for c in tab.courses:
            lines = [
                f"{c.code} — {c.name} ({source.unit}, {tab.label})",
                f"Teorik: {c.theory} | Uygulama: {c.practice} | Lab: {c.lab} | Kredi: {c.credit} | AKTS: {c.akts}",
            ]
            if c.precondition:
                lines.append(f"Ön koşul: {c.precondition}")
            if c.content:
                lines.append(f"İçerik: {c.content}")
            doc_text = "\n".join(lines)
            documents.append(_doc(source, c.code.lower(), c.name, doc_text))

            questions = [
                f"{c.code} dersi nedir?",
                f"{c.name} dersi hakkında bilgi",
                f"{c.code} içeriği nedir?",
            ]
            if c.precondition:
                questions.append(f"{c.code} dersinin ön koşulu nedir?")
            answers.append(_answer(source, questions, doc_text))

    return SourceContent(documents=documents, prepared_answers=answers)


def _extract_tabs(container) -> list[_Tab]:
    tabs = []
    for tab_id, label in _TABS.items():
        pane = container.find(id=tab_id)
        courses = []
        if pane:
            for card in pane.select("div.lesson_card"):
                raw = card.get("data-lesson-data", "{}")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                courses.append(
                    _Course(
                        code=data.get("code", ""),
                        name=collapse_whitespace(data.get("name", "")),
                        theory=int(data.get("theory") or 0),
                        practice=int(data.get("practice") or 0),
                        lab=int(data.get("lab") or 0),
                        credit=float(data.get("credit") or 0),
                        akts=float(data.get("akts") or 0),
                        precondition=collapse_whitespace(data.get("precondition", "")),
                        content=collapse_whitespace(data.get("content", "")),
                    )
                )
        tabs.append(_Tab(id=tab_id, label=label, courses=courses))
    return tabs


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
