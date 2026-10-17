"""Bölümün "İdari Personel" sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı academic_staff ile aynı (div.staff-academician kartları),
ancak kartlarda araştırma konusu ve eğitim alanı bulunmaz; yalnızca ad,
unvan, telefon ve (resim olarak yayınlanan, bkz. `staff_emails`) e-posta bilgisi yer alır.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.ingestion.parsers.departments.software_engineering.staff_emails import (
    card_email,
    known_emails,
)
from atilim_assistant.text import collapse_whitespace, slugify

_PHONE = re.compile(r"\+90[\d ()]{10,}")


@dataclass(frozen=True, slots=True)
class _StaffMember:
    name: str
    title: str
    phone: str
    email: str


def parse(html: str, source: Source) -> SourceContent:
    cards = BeautifulSoup(html, "html.parser").select("div.staff-academician")
    emails = known_emails()
    members = [_parse_card(card, emails) for card in cards]
    if not members:
        raise ValueError(f"{source.url} sayfasında idari personel kartı bulunamadı.")

    return SourceContent(
        documents=[_roster_document(members, source)]
        + [_member_document(m, source) for m in members],
        prepared_answers=_unit_answers(members, source)
        + [a for m in members for a in _member_answers(m, source)],
    )


def _parse_card(card: Tag, emails: dict[str, str]) -> _StaffMember:
    h4 = card.find("h4")
    small = h4.find("small") if h4 else None
    title = collapse_whitespace(small.extract().get_text()).lstrip("/ ") if small else ""
    name = collapse_whitespace(h4.get_text()) if h4 else ""
    phone_m = _PHONE.search(collapse_whitespace(card.get_text(" ")))
    return _StaffMember(
        name=name,
        title=title,
        phone=phone_m.group(0).strip() if phone_m else "",
        email=card_email(card, name, emails),
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
    if m.email:
        lines.append(f"E-posta: {m.email}")
    return _doc(source, slugify(m.name), m.name, "\n".join(lines))


def _unit_answers(members: list[_StaffMember], source: Source) -> list[PreparedAnswer]:
    unit = source.unit
    entries = []
    for m in members:
        label = m.title or "İdari Personel"
        # "Bölüm sekreterine nasıl ulaşırım?" da bu yanıtla karşılanır; iletişim bilgisi eklenir.
        contact = ", ".join(value for value in (m.phone, m.email) if value)
        entries.append(f"{m.name} – {label}" + (f" ({contact})" if contact else ""))
    roster_text = f"{unit} idari kadrosu ({len(members)} kişi):\n" + "\n".join(f"- {e}" for e in entries)
    return [
        _answer(
            source,
            [
                f"{unit} idari personeli kimler?",
                f"{unit} idari kadrosu",
                "Bölüm sekreteri kim?",
                "İdari personele nasıl ulaşırım?",
                "Bölüm sekreterine nasıl ulaşırım?",
                "Bölüm sekreterliğinin telefonu ve maili ne?",
                "Bölüm sekreterliği ile nasıl iletişime geçerim?",
                "Bölümün idari işlerine kim bakıyor?",
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
    if m.email:
        profile_lines.append(f"- E-posta: {m.email}")

    answers.append(
        _answer(
            source,
            [
                m.name,
                f"{m.name} kimdir?",
                f"{m.name} unvanı nedir?",
                f"{m.name} bölümde ne iş yapıyor, görevi ne?",
            ],
            "\n".join(profile_lines),
        )
    )
    contact = [f"telefon: {m.phone}"] if m.phone else []
    contact += [f"e-posta: {m.email}"] if m.email else []
    if contact:
        answers.append(
            _answer(
                source,
                [
                    f"{m.name} telefon numarası nedir?",
                    f"{m.name} iletişim bilgileri",
                    f"{m.name} e-posta, mail adresi nedir?",
                    f"{m.name} nasıl ulaşırım, nasıl iletişime geçerim?",
                ],
                f"**{m.name}** — {', '.join(contact)}",
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
