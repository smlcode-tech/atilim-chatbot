"""Lisans Programı Müfredat sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container):
  - Her yarıyıl bir h3 başlığı ve ardından bir tablo içerir.
  - Tablodaki her ders satırında `data-lesson-data` JSON özniteliği bulunur;
    bu öznitelik ders kodu, adı, Türkçe/İngilizce içerik açıklaması,
    teorik/uygulama saati ve AKTS bilgilerini taşır.
"""

import json
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


@dataclass(frozen=True, slots=True)
class _Course:
    code: str
    name: str
    theory: int
    practice: int
    akts: float
    content: str


@dataclass(frozen=True, slots=True)
class _Semester:
    name: str
    courses: list[_Course] = field(default_factory=list)


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    semesters = _extract_semesters(container)
    if not semesters:
        raise ValueError(f"{source.url} sayfasında yarıyıl/ders tablosu bulunamadı.")

    documents: list[Document] = []
    answers: list[PreparedAnswer] = []

    # Tüm müfredatı özetleyen tek bir belge
    all_lines = [f"{source.unit} Lisans Programı Müfredatı"]
    for sem in semesters:
        all_lines.append(f"\n{sem.name}:")
        for c in sem.courses:
            all_lines.append(f"  {c.code} — {c.name} (AKTS: {c.akts})")
    full_roster = "\n".join(all_lines)
    documents.append(_doc(source, "mufredat-ozet", source.title, full_roster))

    # Hazır yanıt: genel müfredat sorusu
    answers.append(
        _answer(
            source,
            [
                f"{source.unit} müfredatı nedir?",
                "Yazılım mühendisliği bölümünde hangi dersler var?",
                "Lisans programı dersleri neler?",
                "SE bölümü müfredatı",
            ],
            full_roster,
        )
    )

    # Her yarıyıl için ayrı belge ve hazır yanıt
    for sem in semesters:
        sem_lines = [f"{source.unit} {sem.name} dersleri:"]
        for c in sem.courses:
            sem_lines.append(f"- {c.code} {c.name} | Teorik: {c.theory} | Uygulama: {c.practice} | AKTS: {c.akts}")
        sem_text = "\n".join(sem_lines)
        slug = sem.name.lower().replace(". ", "-").replace(" ", "-")
        documents.append(_doc(source, slug, f"{sem.name} Dersleri", sem_text))
        answers.append(
            _answer(
                source,
                [
                    f"{sem.name} dersleri neler?",
                    f"Yazılım mühendisliği {sem.name.lower()} hangi dersleri alıyorum?",
                ],
                sem_text,
            )
        )

    # Her ders için ayrı belge ve hazır yanıt
    for sem in semesters:
        for c in sem.courses:
            lines = [
                f"{c.code} — {c.name} ({source.unit}, {sem.name})",
                f"Teorik: {c.theory} | Uygulama: {c.practice} | AKTS: {c.akts}",
            ]
            if c.content:
                lines.append(f"İçerik: {c.content}")
            doc_text = "\n".join(lines)
            documents.append(_doc(source, c.code.lower(), c.name, doc_text))
            answers.append(
                _answer(
                    source,
                    [
                        f"{c.code} dersi nedir?",
                        f"{c.name} dersi hakkında bilgi",
                        f"{c.code} içeriği nedir?",
                    ],
                    doc_text,
                )
            )

    return SourceContent(documents=documents, prepared_answers=answers)


def _extract_semesters(container) -> list[_Semester]:
    semesters = []
    for h3 in container.find_all("h3"):
        name = collapse_whitespace(h3.get_text())
        table = h3.find_next("table")
        courses = []
        if table:
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if not cells:
                    continue
                link = cells[0].find("a", class_="lesson_card")
                if not link:
                    continue
                try:
                    data = json.loads(link.get("data-lesson-data", "{}"))
                except json.JSONDecodeError:
                    continue
                courses.append(
                    _Course(
                        code=data.get("code", ""),
                        name=collapse_whitespace(data.get("name", "")),
                        theory=int(data.get("theory", 0)),
                        practice=int(data.get("practice", 0)),
                        akts=float(data.get("akts", 0)),
                        content=collapse_whitespace(data.get("content", "")),
                    )
                )
        if courses:
            semesters.append(_Semester(name=name, courses=courses))
    return semesters


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
