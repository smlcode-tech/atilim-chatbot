"""Bölümlerin "Akademik Personel" sayfalarını belgelere çevirir.

Sayfada her kişi bir `div.staff-academician` kartıdır. Her kart için bir belge,
ayrıca "kadroda kimler var" türü sorular için tüm kadroyu listeleyen tek bir belge üretilir.
E-posta adresleri sayfada resim olarak yayınlandığı için alınamaz.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from atilim_assistant.domain import Document, Source
from atilim_assistant.text import collapse_whitespace, slugify

_PHONE = re.compile(r"\+90[\d ()]{10,}")
_RESEARCH_LABEL = "Araştırma Konuları"


@dataclass(frozen=True, slots=True)
class _StaffMember:
    name: str
    role: str
    employment: str
    phone: str
    education: str
    research: str


def parse(html: str, source: Source) -> list[Document]:
    cards = BeautifulSoup(html, "html.parser").select("div.staff-academician")
    members = [_parse_card(card) for card in cards]
    if not members:
        raise ValueError(f"{source.url} sayfasında akademik personel kartı bulunamadı.")
    return [_roster_document(members, source)] + [
        _member_document(member, source) for member in members
    ]


def _parse_card(card: Tag) -> _StaffMember:
    heading = card.find("h4")
    role_tag = heading.find("small")
    role = collapse_whitespace(role_tag.extract().get_text()).lstrip("/ ") if role_tag else ""

    # Kadro türü (ör. yarı zamanlı), kartların arasına konan h3 başlığıyla belirtilir.
    section = card.find_previous_sibling("h3")
    phone = _PHONE.search(collapse_whitespace(card.get_text(" ")))

    education: list[str] = []
    research = ""
    for label, value in _labelled_fields(card):
        if label == _RESEARCH_LABEL:
            research = value
        else:
            education.append(f"{label}: {value}")

    return _StaffMember(
        name=collapse_whitespace(heading.get_text()),
        role=role,
        employment=collapse_whitespace(section.get_text()) if section else "",
        phone=phone.group(0).strip() if phone else "",
        education="; ".join(education),
        research=research,
    )


def _labelled_fields(card: Tag) -> list[tuple[str, str]]:
    """Karttaki `<strong>Etiket</strong>: değer` çiftlerini sırasıyla döndürür."""
    fields = []
    for label in card.find_all("strong"):
        parts = []
        for sibling in label.next_siblings:
            if isinstance(sibling, Tag) and sibling.name == "strong":
                break
            parts.append(sibling.get_text())
        value = collapse_whitespace("".join(parts)).lstrip(": ")
        fields.append((collapse_whitespace(label.get_text()), value))
    return fields


def _member_document(member: _StaffMember, source: Source) -> Document:
    lines = [f"{member.name} — {source.unit} akademik personeli"]
    if member.role:
        lines.append(f"Görev: {member.role}")
    if member.employment:
        lines.append(f"Kadro: {member.employment}")
    if member.phone:
        lines.append(f"Telefon: {member.phone}")
    if member.education:
        lines.append(f"Eğitim: {member.education}")
    lines.append(f"Araştırma Konuları: {member.research or 'Sayfada belirtilmemiş'}")
    return _document(source, slugify(member.name), member.name, "\n".join(lines))


def _roster_document(members: list[_StaffMember], source: Source) -> Document:
    title = f"{source.unit} akademik kadrosu"
    lines = [f"{title} ({len(members)} kişi):"]
    for member in members:
        details = ", ".join(filter(None, [member.role, member.employment]))
        lines.append(f"- {member.name}" + (f" ({details})" if details else ""))
    return _document(source, "kadro", title, "\n".join(lines))


def _document(source: Source, local_id: str, title: str, text: str) -> Document:
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
