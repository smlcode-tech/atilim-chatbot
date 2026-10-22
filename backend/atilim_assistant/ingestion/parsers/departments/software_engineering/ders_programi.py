"""Üniversitenin EduPage ders programından hangi dersi hangi hocanın, hangi gün, saat ve
derslikte verdiğini çıkarır.

Bölüm sayfalarındaki ders kartlarında hoca alanı (`academician_id`) hep boştur, personel
kartlarında da verilen dersler yazmaz. Bu eşleşmenin tek kaynağı ders programıdır:
https://atilim.edupage.org/timetable/ sayfası veriyi JavaScript ile şu uç noktalardan çeker:
  - getTTViewerData: dönemlerin listesi ve öntanımlı (güncel) dönem
  - regularttGetData: dönemin tabloları; `lessons` satırı `subjectid` ile dersi, `teacherids`
    ile hocaları bağlar. Ders adı "SE221-SEC-01-Software Requirements Engineering" biçimindedir.
    `cards` satırı bir `lesson`'ın haftadaki bir oturumudur: `days` gün bit dizisi ("010000" =
    Salı), `period` başladığı ders saati (`periods` tablosu), `classroomids` derslik. Oturum
    `lesson.durationperiods` ders saati sürer.

Program yalnızca güncel dönemi gösterir; o dönem açılmayan dersin hocası bilinmez. Program
alınamazsa ingest durmaz, dersler ve personel hoca bilgisi olmadan indekslenir.
"""

import logging
import re
from dataclasses import dataclass, replace
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
class Meeting:
    """Bir şubenin haftadaki bir oturumu: "Salı", "09:30", "12:20", "Müh. 1025H".
    Derslik atanmamışsa `room` boştur."""

    day: str
    start: str
    end: str
    room: str


@dataclass(frozen=True, slots=True)
class Section:
    """Bir dersin bir şubesi, onu veren hocalar (ders programındaki yazımla) ve haftalık
    oturumları (gün ve saat sırasıyla). Programa yerleştirilmemiş şubenin oturumu yoktur."""

    code: str
    number: str
    name: str
    teachers: tuple[str, ...]
    meetings: tuple[Meeting, ...] = ()


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
    meetings = _meetings(tables)

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
        sessions = (previous.meetings if previous else ()) + meetings.get(lesson["id"], ())
        sections[key] = Section(key[0], section, name.strip(), merged, sessions)
    # Bir şubenin oturumları birkaç `lesson` satırından gelir; tekrarlar atılıp güne göre dizilir.
    day_order = {row["name"]: int(row["id"]) for row in tables["days"].values()}
    return Timetable(
        term=term,
        sections=tuple(
            replace(
                section,
                meetings=tuple(
                    sorted(dict.fromkeys(section.meetings), key=lambda m: (day_order[m.day], m.start))
                ),
            )
            for section in sorted(sections.values(), key=_order)
        ),
    )


def _meetings(tables: dict[str, dict]) -> dict[str, tuple[Meeting, ...]]:
    """`lesson` kimliği → haftalık oturumları. Programa yerleştirilmemiş kartlar (günü ya da
    saati boş) atlanır: olmayan bir saat yazılmamalıdır."""
    days = [row["name"] for row in sorted(tables["days"].values(), key=lambda row: int(row["id"]))]
    periods = {row["period"]: row for row in tables["periods"].values()}
    numbers = sorted(periods, key=int)
    lessons, rooms = tables["lessons"], tables["classrooms"]

    found: dict[str, tuple[Meeting, ...]] = {}
    for card in tables["cards"].values():
        lesson = lessons.get(card["lessonid"])
        if not lesson or card["period"] not in periods:
            continue
        # Oturum başladığı saatten `durationperiods` ders saati sürer; bitiş son saatin bitişidir.
        first = numbers.index(card["period"])
        last = numbers[min(first + int(lesson.get("durationperiods") or 1), len(numbers)) - 1]
        room = ", ".join(rooms[r]["name"].strip() for r in card["classroomids"] if r in rooms)
        found[lesson["id"]] = found.get(lesson["id"], ()) + tuple(
            Meeting(days[index], periods[card["period"]]["starttime"], periods[last]["endtime"], room)
            for index, flag in enumerate(card["days"])
            if flag == "1" and index < len(days)
        )
    return found


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


def meetings_line(meetings: tuple[Meeting, ...]) -> str:
    """Bir şubenin oturumları: "Salı 09:30–12:20 (Müh. 1025H), Perşembe 13:30–14:20"."""
    if not meetings:
        return "programda gün/saat yok"
    return ", ".join(
        f"{m.day} {m.start}–{m.end}" + (f" ({m.room})" if m.room else "") for m in meetings
    )


def schedule_lines(sections: list[Section]) -> list[str]:
    """Şube başına bir satır: "Şube 01 (Fatma Eroğlu): Salı 09:30–12:20 (Müh. 1025H)".

    "SE221 ne zaman, hangi derslikte?" sorusunun yanıtıdır. Şubeler farklı gün, saat ve hocayla
    açılabildiği için her şube ayrı yazılır.
    """
    return [
        f"Şube {s.number} ({', '.join(s.teachers)}): {meetings_line(s.meetings)}" for s in sections
    ]


def teaching_line(sections: list[Section]) -> str:
    """Bir hocanın verdiği dersler, ders başına şubeleriyle:
    "CMPE113 Computer Programming I (Şube 01, 02); FE302 … (Şube 06)".

    `instructors_line`'ın tersi (ders → hocalar yerine hoca → dersler). Hem ingest (personel
    belgeleri) hem sohbet araçları kullanır; ikisinin aynı biçimi vermesi için tek yerdedir.
    """
    by_course: dict[tuple[str, str], list[str]] = {}
    for section in sections:
        by_course.setdefault((section.code, section.name), []).append(section.number)
    return "; ".join(
        f"{code} {name} (Şube {', '.join(numbers)})" for (code, name), numbers in by_course.items()
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
