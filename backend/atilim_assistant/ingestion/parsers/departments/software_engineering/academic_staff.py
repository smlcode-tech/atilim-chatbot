"""Bölümlerin "Akademik Personel" sayfalarını belgelere ve hazır yanıtlara çevirir.

Sayfada her kişi bir `div.staff-academician` kartıdır. Her kart için bir belge,
ayrıca "kadroda kimler var" türü sorular için tüm kadroyu listeleyen tek bir belge üretilir.
Aynı veriden, bu sayfa hakkında en sık sorulan sorular için hazır yanıtlar da üretilir.
E-posta adresleri sayfada resim olarak yayınlandığı için alınamaz.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace, normalize, slugify

_PHONE = re.compile(r"\+90[\d ()]{10,}")
_RESEARCH_LABEL = "Araştırma Konuları"
_UNSPECIFIED = "Sayfada belirtilmemiş"


@dataclass(frozen=True, slots=True)
class _StaffMember:
    name: str
    role: str
    employment: str
    phone: str
    education: str
    research: str


def parse(html: str, source: Source) -> SourceContent:
    cards = BeautifulSoup(html, "html.parser").select("div.staff-academician")
    members = [_parse_card(card) for card in cards]
    if not members:
        raise ValueError(f"{source.url} sayfasında akademik personel kartı bulunamadı.")
    return SourceContent(
        documents=[_roster_document(members, source)]
        + [_member_document(member, source) for member in members],
        prepared_answers=_unit_answers(members, source)
        + _topic_answers(members, source)
        + [answer for member in members for answer in _member_answers(member, source)],
    )


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


def _member_fields(member: _StaffMember) -> list[str]:
    fields = []
    if member.role:
        fields.append(f"Görev: {member.role}")
    if member.employment:
        fields.append(f"Kadro: {member.employment}")
    if member.phone:
        fields.append(f"Telefon: {member.phone}")
    if member.education:
        fields.append(f"Eğitim: {member.education}")
    fields.append(f"{_RESEARCH_LABEL}: {member.research or _UNSPECIFIED}")
    return fields


def _roster_text(members: list[_StaffMember], source: Source) -> str:
    entries = []
    for member in members:
        # Önce görev unvanı (Bölüm Başkanı vb.), yoksa kadro türü (Yarı Zamanlı vb.) göster
        label = member.role or member.employment
        entries.append(f"{member.name} – {label}" if label else member.name)
    return _bullets(f"{source.unit} akademik kadrosu ({len(members)} kişi):", entries)


def _member_document(member: _StaffMember, source: Source) -> Document:
    heading = f"{member.name} — {source.unit} akademik personeli"
    text = "\n".join([heading, *_member_fields(member)])
    return _document(source, slugify(member.name), member.name, text)


def _roster_document(members: list[_StaffMember], source: Source) -> Document:
    title = f"{source.unit} akademik kadrosu"
    return _document(source, "kadro", title, _roster_text(members, source))


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


def _member_answers(member: _StaffMember, source: Source) -> list[PreparedAnswer]:
    name = member.name
    profile = "\n".join(
        [f"**{name}** — {source.unit} akademik personeli", ""]
        + [f"- {field}" for field in _member_fields(member)]
    )
    return [
        _answer(
            source,
            [
                name,
                f"{name} kimdir?",
                f"{name} hakkında bilgi verir misin?",
                f"{name} görevi ve unvanı nedir?",
            ],
            profile,
        ),
        _answer(
            source,
            [
                f"{name} araştırma konuları neler?",
                f"{name} hangi alanda, hangi alanlarda çalışıyor?",
                f"{name} uzmanlık ve çalışma alanı nedir?",
            ],
            f"**{name}** — araştırma konuları: {member.research or _UNSPECIFIED}",
        ),
        _answer(
            source,
            [
                f"{name} telefon numarası nedir?",
                f"{name} iletişim bilgileri neler?",
                f"{name} e-posta, mail adresi nedir?",
                f"{name} nasıl ulaşırım, nasıl ulaşabilirim?",
            ],
            f"**{name}** — telefon: {member.phone or _UNSPECIFIED.lower()}. "
            "E-posta adresi için kaynak sayfaya bakabilirsin.",
        ),
        _answer(
            source,
            [
                f"{name} eğitim bilgileri neler?",
                f"{name} hangi üniversiteden mezun?",
                f"{name} lisans, yüksek lisans ve doktorasını nerede yaptı?",
            ],
            f"**{name}** — eğitim: {member.education or _UNSPECIFIED}",
        ),
    ]


def _unit_answers(members: list[_StaffMember], source: Source) -> list[PreparedAnswer]:
    unit = source.unit
    roster_questions = [
        "akademik kadrosunda kimler var?",
        "akademik personelini tanıtır mısın?",
        "akademisyenler, hocalar ve öğretim üyeleri kimler?",
        "kaç hoca, kaç öğretim üyesi var?",
    ]
    answers = [
        _answer(
            source,
            # Birim adı anılmadan sorulan genel sorular da ("Hocalar kimler?") kadroyu getirir.
            [f"{unit} {question}" for question in roster_questions] + roster_questions,
            _roster_text(members, source),
        )
    ]

    officers = [member for member in members if member.role]
    if officers:
        answers.append(
            _answer(
                source,
                [f"{unit} {member.role} kim?" for member in officers]
                + [f"{unit} bölüm başkanı, başkan yardımcısı ve yöneticileri kimler?"],
                _bullets(
                    f"{unit} görevlileri:",
                    [f"{member.name} ({member.role})" for member in officers],
                ),
            )
        )

    for employment in dict.fromkeys(member.employment for member in members if member.employment):
        names = [member.name for member in members if member.employment == employment]
        answers.append(
            _answer(source, [f"{unit} {employment} kimler?"], _bullets(f"{unit} — {employment}:", names))
        )
    return answers


def _topic_answers(members: list[_StaffMember], source: Source) -> list[PreparedAnswer]:
    """Sayfada geçen her araştırma konusu için o konuda çalışanların listesi."""
    topics: dict[str, str] = {}
    for member in members:
        for topic in member.research.rstrip(". ").split(","):
            if normalize(topic):
                topics.setdefault(normalize(topic), topic.strip())

    answers = []
    for key, topic in topics.items():
        # Konu, başka bir konunun parçası olarak geçiyorsa da sayılır
        # ("Makine Öğrenmesi" ⊂ "Yapay Zekâ ve Makine Öğrenmesi").
        names = [m.name for m in members if f" {key} " in f" {normalize(m.research)} "]
        answers.append(
            _answer(
                source,
                [
                    f"{topic} üzerine çalışan akademisyenler kimler?",
                    f"{topic} alanında çalışan hocalar ve öğretim üyeleri kimler?",
                    f"{topic} konusunda çalışan, {topic} ile ilgilenen hoca var mı?",
                ],
                _bullets(f"{source.unit} — araştırma konuları arasında {topic} olanlar:", names),
            )
        )
    return answers


def _bullets(heading: str, items: list[str]) -> str:
    return "\n".join([heading, *(f"- {item}" for item in items)])


def _answer(source: Source, questions: list[str], answer: str) -> PreparedAnswer:
    return PreparedAnswer(
        source_id=source.id,
        source_title=source.title,
        url=source.url,
        questions=questions,
        answer=answer,
    )
