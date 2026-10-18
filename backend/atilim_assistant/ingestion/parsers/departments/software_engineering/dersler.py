"""Lisans Programı "Dersler" sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div#lessons-wrapper):
  - Üç sekme: Zorunlu Dersler | Alan Seçmeli Dersler | Alan Dışı Seçmeli Dersler
  - Her sekmede div.lesson_card'lar; `data-lesson-data` JSON'u ders bilgilerini taşır.
"""

import json
from dataclasses import asdict, dataclass, field

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.ingestion.parsers.departments.software_engineering import ders_programi
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
    # Ders kartlarında hoca alanı boştur; hoca, güncel dönemin ders programından eklenir.
    timetable = ders_programi.current()
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
    # Tüm ders listesi belge olarak indekslenmez: model bağlamının tek başına sınırını aşar ve
    # aynı bilgi sekme özetlerinde zaten var. Yalnızca hazır yanıt olarak verilir.
    answers.append(
        _answer(
            source,
            [
                f"{source.unit} dersleri nelerdir?",
                "Yazılım mühendisliğinde hangi dersler var?",
                "SE bölümü ders listesi",
                "Bölümde hangi dersleri alacağım?",
                "Tüm derslerin listesi",
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
                    f"Hangi {tab.label.lower()} var?",
                    f"{tab.label} kaç tane, kaç AKTS?",
                ],
                tab_text,
            )
        )

    # "Seçmeli dersler neler?" iki sekmeyi birden sorar. Birleşik liste bağlam bütçesine
    # sığmayacağı için belge değil, yalnızca hazır yanıt olur.
    electives = [tab for tab in tabs if tab.id != "required_les" and tab.courses]
    if electives:
        elective_text = "\n\n".join(
            "\n".join(
                [f"{tab.label} ({len(tab.courses)} ders):"]
                + [f"- {c.code} {c.name} | AKTS:{c.akts}" for c in tab.courses]
            )
            for tab in electives
        )
        answers.append(
            _answer(
                source,
                [
                    "Seçmeli dersler nelerdir?",
                    "Seçmeli ders listesi",
                    "Hangi seçmeli dersleri alabilirim?",
                    "Seçmeli ders seçenekleri neler?",
                ],
                f"{source.unit} seçmeli dersleri:\n\n{elective_text}",
            )
        )

    # Her ders için ayrı belge + hazır yanıt
    for tab in tabs:
        seen: set[str] = set()
        for c in tab.courses:
            lines = [
                f"{c.code} — {c.name} ({source.unit}, {tab.label})",
                f"Teorik: {c.theory} | Uygulama: {c.practice} | Lab: {c.lab} | Kredi: {c.credit} | AKTS: {c.akts}",
            ]
            sections = timetable.sections_of_course(c.code) if timetable else []
            if sections:
                instructors = ders_programi.instructors_line(sections)
                lines.append(f"Öğretim elemanı ({timetable.term}): {instructors}")
            elif timetable:
                # "Kim veriyor?" sorusu bu yanıta düşebilir; hocanın neden yazmadığı söylenir.
                lines.append(
                    f"Öğretim elemanı: {timetable.term} ders programında bu ders açılmamış."
                )
            if c.precondition:
                lines.append(f"Ön koşul: {c.precondition}")
            if c.content:
                lines.append(f"İçerik: {c.content}")
            doc_text = "\n".join(lines)
            base = f"{tab.id}-{c.code.lower()}"
            local_id = base if base not in seen else f"{base}-2"
            seen.add(local_id)
            documents.append(_doc(source, local_id, c.name, doc_text))

            questions = [
                f"{c.code} dersi nedir?",
                f"{c.name} dersi hakkında bilgi",
                f"{c.code} içeriği nedir?",
                f"{c.code} kaç AKTS, kaç kredi?",
                f"{c.name} dersi kaç AKTS, kaç kredi?",
                f"{c.code} haftada kaç saat teorik, uygulama ve lab?",
                f"{c.code} zorunlu mu, seçmeli mi?",
            ]
            if c.content:
                questions += [
                    f"{c.code} dersinin konuları neler, neler anlatılıyor?",
                    f"{c.name} dersinde ne öğreniliyor?",
                ]
            if sections:
                questions += [
                    f"{c.code} dersini kim veriyor, hocası kim?",
                    f"{c.name} dersine hangi hoca giriyor?",
                ]
            if c.precondition:
                questions += [
                    f"{c.code} dersinin ön koşulu nedir?",
                    f"{c.name} dersini almak için önce hangi dersi almalıyım?",
                ]
            answers.append(_answer(source, questions, doc_text))

    courses = [
        {**asdict(course), "category": tab.label} for tab in tabs for course in tab.courses
    ]
    return SourceContent(
        documents=documents, prepared_answers=answers, records={"courses": courses}
    )


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
