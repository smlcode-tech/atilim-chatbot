"""Üniversitenin EduPage ders programından hangi dersi hangi hocanın verdiğini çıkarır.

Bölüm sayfalarındaki ders kartlarında hoca alanı (`academician_id`) hep boştur, personel
kartlarında da verilen dersler yazmaz. Bu eşleşmenin tek kaynağı ders programıdır:
https://atilim.edupage.org/timetable/ sayfası veriyi JavaScript ile şu uç noktalardan çeker:
  - getTTViewerData: dönemlerin listesi ve öntanımlı (güncel) dönem
  - regularttGetData: dönemin tabloları; `lessons` satırı `subjectid` ile dersi, `teacherids`
    ile hocaları bağlar. Ders adı "SE221-SEC-01-Software Requirements Engineering" biçimindedir.

Program yalnızca güncel dönemi gösterir; o dönem açılmayan dersin hocası bilinmez. Program
alınamazsa ingest durmaz, dersler ve personel hoca bilgisi olmadan indekslenir.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import httpx

from atilim_assistant.text import normalize

_SERVER = "https://atilim.edupage.org/timetable/server"
PUBLIC_URL = "https://atilim.edupage.org/timetable/"
# Sayfa herkese açık; istek, tarayıcının gönderdiği boş oturum özetiyle yapılır.
_GSH = "00000000"
# Yeni öğretim yılı EduPage'de 1 Ağustos'ta başlar (`schoolyear_turnover`).
_TURNOVER_MONTH = 8

# Programdaki ders adı: kod, şube numarası ve ad ("SE221-SEC-01-Software Requirements …").
_SUBJECT = re.compile(r"^([A-ZÇĞİÖŞÜ]{2,5}) ?(\d{3}[A-Z]?)-SEC-(\d+)-(.*)$")
# Hocası henüz atanmamış şubeler "Staff", "STAFF1" gibi yer tutucularla görünür.
_PLACEHOLDER = re.compile(r"^staff\d*$")
# Ad karşılaştırmasında atılan unvan sözcükleri (normalleştirilmiş): personel sayfası adları
# unvanla ("Prof. Dr. …"), ders programı unvansız yazar.
_TITLE_WORDS = frozenset({"prof", "doc", "dr", "ogr", "uyesi", "gor", "ars", "yrd"})

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Section:
    """Bir dersin bir şubesi ve onu veren hocalar (ders programındaki yazımla)."""

    code: str
    number: str
    name: str
    teachers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Timetable:
    """Bir dönemin tüm şubeleri. `term` dönemin adıdır ("2025-2026 Güz" gibi); yanıtlarda
    bilginin hangi döneme ait olduğunu söylemek için taşınır."""

    term: str
    sections: tuple[Section, ...]

    def sections_of_course(self, code: str) -> list[Section]:
        """Dersin bu dönemki şubeleri; ders açılmadıysa boş."""
        return [section for section in self.sections if section.code == code]

    def sections_of_teacher(self, name: str) -> list[Section]:
        """Personel sayfasındaki adla eşleşen hocanın şubeleri; adlar iki kaynakta farklı
        yazıldığı için eşitlik değil `same_person` kullanılır."""
        return [
            section
            for section in self.sections
            if any(same_person(teacher, name) for teacher in section.teachers)
        ]


@lru_cache(maxsize=1)
def current() -> Timetable | None:
    """Güncel dönemin programı; ingest boyunca bir kez çekilir. Alınamazsa None.

    Önbelleklenir çünkü üç yer çağırır (dersler, akademik personel, `cli ingest`) ve program
    büyük bir yanıttır. Hata yutulup None döner: EduPage kapalıyken bölüm sayfalarının
    indekslenmesi engellenmemelidir.
    """
    try:
        versions = _call("ttviewer.js", "getTTViewerData", [None, _school_year(date.today())])
        number = versions["regular"]["default_num"]
        term = next(
            timetable["text"]
            for timetable in versions["regular"]["timetables"]
            if timetable["tt_num"] == number
        )
        return parse(term, _call("regulartt.js", "regularttGetData", [None, number]))
    except (httpx.HTTPError, KeyError, StopIteration, ValueError) as error:
        logger.warning("Ders programı alınamadı, hoca bilgisi eklenmeyecek: %s", error)
        return None


def parse(term: str, data: dict) -> Timetable:
    """regularttGetData yanıtını şubelere çevirir; hocasız ya da kodsuz dersler atlanır."""
    tables = {
        table["id"]: {row["id"]: row for row in table.get("data_rows", [])}
        for table in data["dbiAccessorRes"]["tables"]
    }
    subjects, teachers = tables["subjects"], tables["teachers"]

    # Aynı şube haftada birkaç kez (birkaç `lesson` satırıyla) geçer; bir kez sayılır.
    sections: dict[tuple[str, str], Section] = {}
    for lesson in tables["lessons"].values():
        match = _SUBJECT.match(subjects.get(lesson["subjectid"], {}).get("name", "").strip())
        names = tuple(
            teachers[teacher]["short"].strip()
            for teacher in lesson["teacherids"]
            if teacher in teachers and not _PLACEHOLDER.match(normalize(teachers[teacher]["short"]))
        )
        if not match or not names:
            continue
        subject, number, section, name = match.groups()
        key = (f"{subject}{number}", section)
        previous = sections.get(key)
        merged = tuple(dict.fromkeys((previous.teachers if previous else ()) + names))
        sections[key] = Section(key[0], section, name.strip(), merged)
    return Timetable(term=term, sections=tuple(sorted(sections.values(), key=_order)))


def same_person(teacher: str, staff_name: str) -> bool:
    """Programdaki ad ("Sacit Uluırmak") personel sayfasındaki adla ("Öğr. Gör. Nimet Sacit
    ULUIRMAK") aynı kişi mi: soyadı aynı ve programdaki her ad personel adında geçiyor."""
    short, full = name_tokens(teacher), name_tokens(staff_name)
    # Yalnızca soyadı yazılmışsa aynı soyadlı herkesle eşleşirdi; en az bir ad gerekir.
    if len(short) < 2 or len(full) < 2 or short[-1] != full[-1]:
        return False
    return set(short[:-1]) <= set(full[:-1])


def instructors_line(sections: list[Section]) -> str:
    """Tek hoca varsa yalnızca adı; birden çoksa her hocanın şubeleri:
    "Fatma Eroğlu (Şube 01, 02); Serdar Ay (Şube 03)"."""
    by_teacher: dict[str, list[str]] = {}
    for section in sections:
        for teacher in section.teachers:
            by_teacher.setdefault(teacher, []).append(section.number)
    if len(by_teacher) == 1:
        return next(iter(by_teacher))
    return "; ".join(
        f"{teacher} (Şube {', '.join(numbers)})" for teacher, numbers in by_teacher.items()
    )


def name_tokens(name: str) -> list[str]:
    """Unvanları atılmış, normalleştirilmiş ad sözcükleri: "Prof. Dr. Ali YAZICI" → [ali, yazici]."""
    return [token for token in normalize(name).split() if token not in _TITLE_WORDS]


def _order(section: Section) -> tuple[str, str]:
    """Şubelerin sırası: koda, sonra şube numarasına göre; çıktı her ingest'te aynı sırada olur."""
    return section.code, section.number


def _school_year(today: date) -> int:
    """EduPage'in beklediği öğretim yılı: Ağustos'tan önce bir önceki yıl ("2025" = 2025-2026)."""
    return today.year if today.month >= _TURNOVER_MONTH else today.year - 1


def _call(script: str, function: str, args: list) -> dict:
    """EduPage sunucusundaki bir işlevi çağırır; tarayıcının yaptığı isteğin aynısıdır.
    Bu belgelenmiş bir API değildir: EduPage biçimi değiştirirse `current()` None döner."""
    response = httpx.post(
        f"{_SERVER}/{script}",
        params={"__func": function},
        json={"__args": args, "__gsh": _GSH},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["r"]
