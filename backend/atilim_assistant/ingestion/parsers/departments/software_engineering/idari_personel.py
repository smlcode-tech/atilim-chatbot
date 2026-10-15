"""Bölümün "İdari Personel" sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı academic_staff ile aynı (div.staff-academician kartları),
ancak kartlarda araştırma konusu ve eğitim alanı bulunmaz; yalnızca ad,
unvan ve telefon bilgisi yer alır.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace, slugify

_PHONE = re.compile(r"\+90[\d ()]{10,}")


@dataclass(frozen=True, slots=True)
class _StaffMember:
    name: str
    title: str
    phone: str


def parse(html: str, source: Source) -> SourceContent:
    cards = BeautifulSoup(html, "html.parser").select("div.staff-academician")
    members = [_parse_card(card) for card in cards]
    if not members:
        raise ValueError(f"{source.url} sayfasında idari personel kartı bulunamadı.")

    return SourceContent(
        documents=[_roster_document(members, source)]
        + [_member_document(m, source) for m in members],
        prepared_answers=_unit_answers(members, source)
        + [a for m in members for a in _member_answers(m, source)],
    )


def _parse_card(card: Tag) -> _StaffMember:
    h4 = card.find("h4")
    small = h4.find("small") if h4 else None
    title = collapse_whitespace(small.extract().get_text()).lstrip("/ ") if small else ""
    name = collapse_whitespace(h4.get_text()) if h4 else ""
    phone_m = _PHONE.search(collapse_whitespace(card.get_text(" ")))
    return _StaffMember(
        name=name,
        title=title,
        phone=phone_m.group(0).strip() if phone_m else "",
    )


def _roster_document(members: list[_StaffMember], source: Source) -> Document:
    entries = []
    for m in members:
        label = m.title or "İdari Personel"
        entries.append(f"{m.name} – {label}")
    text = f"{source.unit} idari kadrosu ({len(members)} kişi):\n" + "\n".join(f"- {e}" for e in entries)
    return _doc(source, "kadro", f"{source.unit} idari kadrosu", text)


def _member_document(m: _StaffMember, source: Source) -> Document:
    lines = [f"{m.name} — {source.unit} idari personeli"]
    if m.title:
        lines.append(f"Unvan: {m.title}")
    if m.phone:
        lines.append(f"Telefon: {m.phone}")
    return _doc(source, slugify(m.name), m.name, "\n".join(lines))


def _unit_answers(members: list[_StaffMember], source: Source) -> list[PreparedAnswer]:
    unit = source.unit
    entries = []
    for m in members:
        label = m.title or "İdari Personel"
        entries.append(f"{m.name} – {label}")
    roster_text = f"{unit} idari kadrosu ({len(members)} kişi):\n" + "\n".join(f"- {e}" for e in entries)
    return [
        _answer(
            source,
            [
                f"{unit} idari personeli kimler?",
                f"{unit} idari kadrosu",
                "Bölüm sekreteri kim?",
                "İdari personele nasıl ulaşırım?",
            ],
            roster_text,
        )
    ]


def _member_answers(m: _StaffMember, source: Source) -> list[PreparedAnswer]:
    answers = []
    profile_lines = [f"**{m.name}** — {source.unit} idari personeli"]
    if m.title:
        profile_lines.append(f"- Unvan: {m.title}")
    if m.phone:
        profile_lines.append(f"- Telefon: {m.phone}")

    answers.append(
        _answer(
            source,
            [
                m.name,
                f"{m.name} kimdir?",
                f"{m.name} unvanı nedir?",
            ],
            "\n".join(profile_lines),
        )
    )
    if m.phone:
        answers.append(
            _answer(
                source,
                [
                    f"{m.name} telefon numarası nedir?",
                    f"{m.name} iletişim bilgileri",
                ],
                f"**{m.name}** — telefon: {m.phone}",
            )
        )
    return answers


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
