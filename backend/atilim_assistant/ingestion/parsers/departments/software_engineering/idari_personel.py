"""Bölümün "İdari Personel" sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı academic_staff ile aynı (div.staff-academician kartları),
ancak kartlarda araştırma konusu ve eğitim alanı bulunmaz; yalnızca ad,
unvan, telefon ve (resim olarak yayınlanan, bkz. `staff_emails`) e-posta bilgisi yer alır.
"""

import re
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup, Tag

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for
from atilim_assistant.ingestion.parsers.departments.software_engineering.staff_emails import (
    card_email,
    known_emails,
)
from atilim_assistant.text import collapse_whitespace, slugify

# Kartta telefon ayrı bir alanda değil, düz metin içinde durur; +90 ile başlayan dizi aranır.
_PHONE = re.compile(r"\+90[\d ()]{10,}")


@dataclass(frozen=True, slots=True)
class _StaffMember:
    """Bir idari personel kartı; katalogdaki `admin_staff` kaydının alanları da bunlardır."""

    name: str
    title: str
    phone: str
    email: str


def parse(html: str, source: Source) -> SourceContent:
    """Kadro listesi, kişi başına belge, hazır yanıtlar ve katalog kaydı (`personel_bilgisi`
    aracı idari personeli buradan bulur)."""
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
        # Akademik kadrodan ayrı anahtar: katalog kaydı kaynak başına bütünüyle değiştirilir.
        records={"admin_staff": [asdict(m) for m in members]},
    )


def _parse_card(card: Tag, emails: dict[str, str]) -> _StaffMember:
    """Kartı alanlara ayırır. Unvan başlıktaki `<small>` içindedir; adın içine karışmasın diye
    önce çıkarılır, kalan başlık metni addır."""
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
    """Tüm idari kadro tek belgede; "idari personel kimler?" tek aramada bütün listeyi bulsun."""
    entries = []
    for m in members:
        label = m.title or "İdari Personel"
        entries.append(f"{m.name} – {label}")
    text = f"{source.unit} idari kadrosu ({len(members)} kişi):\n" + "\n".join(f"- {e}" for e in entries)
    return doc_for(source, "kadro", f"{source.unit} idari kadrosu", text)


def _member_document(m: _StaffMember, source: Source) -> Document:
    """Kişi başına belge; adla sorulan soru tek kişinin bilgisini bulur. Boş alanlar yazılmaz."""
    lines = [f"{m.name} — {source.unit} idari personeli"]
    if m.title:
        lines.append(f"Unvan: {m.title}")
    if m.phone:
        lines.append(f"Telefon: {m.phone}")
    if m.email:
        lines.append(f"E-posta: {m.email}")
    return doc_for(source, slugify(m.name), m.name, "\n".join(lines))


def _unit_answers(members: list[_StaffMember], source: Source) -> list[PreparedAnswer]:
    """Birim düzeyindeki hazır yanıt: kadro listesi, iletişim bilgileriyle birlikte. Kullanıcı
    çoğu zaman adı değil görevi bilir ("bölüm sekreteri")."""
    unit = source.unit
    entries = []
    for m in members:
        label = m.title or "İdari Personel"
        # "Bölüm sekreterine nasıl ulaşırım?" da bu yanıtla karşılanır; iletişim bilgisi eklenir.
        contact = ", ".join(value for value in (m.phone, m.email) if value)
        entries.append(f"{m.name} – {label}" + (f" ({contact})" if contact else ""))
    roster_text = f"{unit} idari kadrosu ({len(members)} kişi):\n" + "\n".join(f"- {e}" for e in entries)
    return [
        answer_for(
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
    """Kişi başına profil yanıtı ve (bilgi varsa) iletişim yanıtı. İletişim bilgisi yoksa o
    yanıt üretilmez: "telefonu ne?" sorusu boş bir yanıta değil modele gitmelidir."""
    answers = []
    profile_lines = [f"**{m.name}** — {source.unit} idari personeli"]
    if m.title:
        profile_lines.append(f"- Unvan: {m.title}")
    if m.phone:
        profile_lines.append(f"- Telefon: {m.phone}")
    if m.email:
        profile_lines.append(f"- E-posta: {m.email}")

    answers.append(
        answer_for(
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
            answer_for(
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
