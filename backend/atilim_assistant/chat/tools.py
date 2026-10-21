"""Modelin soru yanıtlarken çağırdığı araçlar: katalog sorguları ve belge araması.

Kullanıcının söyleyişini (kısaltma, eş anlamlı, takip sorusu) model yorumlar; araçlar yalnızca
veriyi kesin olarak döndürür. Böylece her söyleyiş için kalıp ya da kural yazmak gerekmez.
Liste ve süzme gerektiren sorular ("bu hocalardan hangileri MATH dersi veriyor?") tüm kayıtlar
üzerinde hesaplanır; metin aramasının getirdiği birkaç parçaya sığmaları gerekmez.
"""

import inspect
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from atilim_assistant.domain import Citation, Document
from atilim_assistant.ingestion.parsers.departments.software_engineering.ders_programi import (
    Section,
    instructors_line,
    name_tokens,
    same_person,
)
from atilim_assistant.retrieval.catalog import SECTIONS, Catalog
from atilim_assistant.text import FILLER_WORDS, correct_course_codes, normalize, stem

# Tek bir araç sonucunun sınırları: model bağlamı ve dakikalık token kotası sınırlıdır.
_MAX_COURSES = 30
_MAX_DOCUMENT_CHARS = 6000
_MAX_RESEARCH_CHARS = 100

logger = logging.getLogger(__name__)

_COURSE_CODE = re.compile(r"\b([a-z]{2,5}) ?(\d{3}[a-z]?)\b")
_MIN_WORD = 3


@dataclass(frozen=True, slots=True)
class ToolResult:
    text: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class _Course:
    code: str
    name: str
    record: dict | None = None
    sections: list[Section] = field(default_factory=list)
    words: frozenset[str] = frozenset()


def _function(name: str, description: str, **parameters: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {key: {"type": "string", "description": text}
                               for key, text in parameters.items()},
                "required": list(parameters),
            },
        },
    }


DEFINITIONS = [
    _function(
        "ders_ara",
        "Tüm üniversitedeki dersleri ve bu dönem kimin verdiğini bulur. Tam kod (SE212), kod "
        "öneki (MATH = matematik, PHYS = fizik, SE = yazılım müh., CMPE = bilgisayar müh., "
        "ENG = İngilizce) ya da ders adındaki sözcüklerle arar. Bölüm dışı ders adları "
        "İngilizcedir; Türkçe sözcük sonuç vermezse İngilizcesini ya da kod önekini dene.",
        sorgu="Ders kodu, kod öneki ya da ad sözcükleri",
    ),
    _function(
        "ders_detayi",
        "Bir dersin kredi, AKTS, saat, ön koşul, içerik ve bu dönemki hocalarını getirir.",
        kod="Ders kodu, ör. SE212",
    ),
    _function(
        "hocanin_dersleri",
        "Bir öğretim elemanının bu dönem ders programında verdiği dersler (tüm üniversite).",
        ad="Hocanın adı ya da soyadı",
    ),
    _function(
        "bolum_kadrosu",
        "Yazılım Mühendisliği Bölümü akademik kadrosu: unvan, görev, araştırma konuları ve "
        "her hocanın bu dönem verdiği dersler. Bölüm hocalarıyla ilgili liste ve süzme "
        "soruları için kullan.",
    ),
    _function(
        "personel_bilgisi",
        "Yazılım Mühendisliği Bölümü'ndeki bir hocanın tüm bilgileri: iletişim, eğitim, "
        "araştırma konuları, görevi ve bu dönem verdiği dersler. İdari personelin (bölüm "
        "sekreteri vb.) unvan ve iletişim bilgilerini de verir.",
        ad="Kişinin adı ya da soyadı",
    ),
    _function(
        "belge_ara",
        "Bölüm sayfalarında metin araması: staj, ortak eğitim, SSS, kontenjan, Erasmus, "
        "dilekçeler, komiteler, müfredat, program çıktıları, bölüm tanıtımı ve benzeri.",
        sorgu="Aranacak konu",
    ),
]


class Tools:
    def __init__(self, catalog: Catalog, retriever) -> None:
        self._catalog = catalog
        self._retriever = retriever
        self._courses = _course_index(catalog)
        self._handlers: dict[str, Callable[..., ToolResult]] = {
            "ders_ara": self.ders_ara,
            "ders_detayi": self.ders_detayi,
            "hocanin_dersleri": self.hocanin_dersleri,
            "bolum_kadrosu": self.bolum_kadrosu,
            "personel_bilgisi": self.personel_bilgisi,
            "belge_ara": self.belge_ara,
        }

    @property
    def term(self) -> str:
        return self._catalog.timetable.term

    def correct(self, text: str) -> str:
        """Tek harfle yanlış yazılmış ders kodunu düzeltir ("MATF276" → "MATH276")."""
        known = frozenset(code.lower() for code in self._courses) | self._retriever.course_codes
        return correct_course_codes(text, known)

    def suggest(self, question: str, limit: int) -> list[str]:
        """Soruya en yakın, yanıtı olan sorular; bkz. `HybridRetriever.similar_questions`."""
        return self._retriever.similar_questions(question, limit)

    def run(self, name: str, arguments: str) -> ToolResult:
        """Modelin istediği aracı çalıştırır; hatalı çağrı modele açıklama olarak döner ki
        düzeltip yeniden deneyebilsin."""
        handler = self._handlers.get(name)
        if handler is None:
            return ToolResult(f"Bilinmeyen araç: {name}")
        try:
            args = json.loads(arguments or "{}")
            # Parametresiz araçlar bazen boş anahtarlı argümanla çağrılıyor ({"": {}}).
            accepted = inspect.signature(handler).parameters
            return handler(**(args if accepted else {}))
        except (json.JSONDecodeError, TypeError) as error:
            return ToolResult(f"Geçersiz argüman: {error}")
        except Exception:
            # Aracın kendi hatası (ör. embedding servisine ulaşılamaması) modelin hatası değildir;
            # yükselirse model kesintisi sayılır, kota sanılırsa model bir saat kapatılırdı.
            logger.exception("Araç %s çalışmadı", name)
            return ToolResult(
                f"{name} şu anda çalışmıyor; başka bir araçla dene ya da bildiklerinle yanıtla."
            )

    def ders_ara(self, sorgu: str) -> ToolResult:
        query = normalize(self.correct(sorgu))
        exact = [code for code in _codes_in(query) if code in self._courses]
        prefixes = {token for token in query.split() if token.isalpha()} & {
            _prefix(code) for code in self._courses
        }
        words = {
            stem(token)
            for token in query.split()
            if len(token) >= _MIN_WORD and token not in FILLER_WORDS and token not in prefixes
        }

        scored = []
        for code, course in self._courses.items():
            score = (code in exact, _prefix(code) in prefixes, len(words & course.words))
            if any(score):
                scored.append((score, code))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        found = [self._courses[code] for _, code in scored]
        if not found:
            return ToolResult(f"'{sorgu}' ile eşleşen ders yok. Başka sözcük ya da kod öneki dene.")

        lines = [self._summary(course) for course in found[:_MAX_COURSES]]
        if len(found) > _MAX_COURSES:
            lines.append(f"(+{len(found) - _MAX_COURSES} ders daha; aramayı daralt.)")
        return ToolResult("\n".join(lines), self._citations("courses", SECTIONS))

    def ders_detayi(self, kod: str) -> ToolResult:
        codes = _codes_in(normalize(self.correct(kod))) or [normalize(kod).replace(" ", "")]
        course = self._courses.get(codes[0].upper())
        if course is None:
            return ToolResult(f"{kod} kodlu ders bulunamadı. ders_ara ile ara.")
        lines = [f"{course.code} — {course.name}"]
        if course.record:
            record = course.record
            lines += [
                f"Bölüm programında: {record['category']}",
                f"Teorik: {record['theory']} | Uygulama: {record['practice']} | Lab: {record['lab']}"
                f" | Kredi: {record['credit']} | AKTS: {record['akts']}",
            ]
            if record["precondition"]:
                lines.append(f"Ön koşul: {record['precondition']}")
            if record["content"]:
                lines.append(f"İçerik: {record['content']}")
        else:
            lines.append("Yazılım Mühendisliği lisans programının ders listesinde yok.")
        lines.append(self._instructors(course))
        return ToolResult("\n".join(lines), self._citations("courses", SECTIONS))

    def hocanin_dersleri(self, ad: str) -> ToolResult:
        teachers = sorted(
            {t for s in self._catalog.timetable.sections for t in s.teachers if _same(ad, t)}
        )
        if not teachers:
            return ToolResult(f"{self.term} ders programında '{ad}' adlı öğretim elemanı yok.")
        lines = [
            f"{teacher}: {_teaching(self._catalog.timetable.sections_of_teacher(teacher))}"
            for teacher in teachers
        ]
        return ToolResult(f"{self.term} ders programı:\n" + "\n".join(lines), self._citations(SECTIONS))

    def bolum_kadrosu(self) -> ToolResult:
        lines = []
        for member in self._catalog.staff:
            parts = [member["name"]]
            if member["role"] or member["employment"]:
                parts.append(member["role"] or member["employment"])
            research = member["research"]
            if research:
                clipped = research[:_MAX_RESEARCH_CHARS]
                parts.append(f"Araştırma: {clipped}{'…' if len(research) > len(clipped) else ''}")
            parts.append(f"Bu dönem dersleri: {self._courses_of(member['name']) or 'yok'}")
            lines.append(" | ".join(parts))
        if not lines:
            return ToolResult("Kadro bilgisi yok.")
        heading = f"Yazılım Mühendisliği Bölümü akademik kadrosu ({len(lines)} kişi; dersler: {self.term}):"
        return ToolResult("\n".join([heading, *lines]), self._citations("staff", SECTIONS))

    def personel_bilgisi(self, ad: str) -> ToolResult:
        members = [m for m in self._catalog.staff if _same(ad, m["name"])]
        admins = [m for m in self._catalog.admin_staff if _same(ad, m["name"])]
        if not members and not admins:
            return ToolResult(f"Bölüm kadrosunda '{ad}' yok. hocanin_dersleri ile tüm üniversitede ara.")
        blocks = [
            "\n".join(
                [f"{admin['name']} (idari personel)"]
                + [f"{label}: {admin[key]}"
                   for label, key in (("Unvan", "title"), ("Telefon", "phone"), ("E-posta", "email"))
                   if admin[key]]
            )
            for admin in admins
        ]
        for member in members:
            fields = [member["name"]]
            for label, key in (("Görev", "role"), ("Kadro", "employment"), ("Telefon", "phone"),
                               ("E-posta", "email"), ("Eğitim", "education"),
                               ("Araştırma konuları", "research")):
                if member[key]:
                    fields.append(f"{label}: {member[key]}")
            fields.append(f"{self.term} dersleri: {self._courses_of(member['name']) or 'yok'}")
            blocks.append("\n".join(fields))
        keys = ["staff", SECTIONS] if members else []
        return ToolResult("\n\n".join(blocks), self._citations(*keys, *(["admin_staff"] if admins else [])))

    def belge_ara(self, sorgu: str) -> ToolResult:
        documents: list[Document] = []
        used = 0
        for document in self._retriever.retrieve(sorgu):
            if used + len(document.text) > _MAX_DOCUMENT_CHARS:
                continue
            documents.append(document)
            used += len(document.text)
        if not documents:
            return ToolResult(f"'{sorgu}' ile ilgili belge bulunamadı.")
        text = "\n\n---\n\n".join(f"[{d.source_title}] {d.title}\n{d.text}" for d in documents)
        pages = {document.url: document.source_title for document in documents}
        return ToolResult(text, [Citation(title=title, url=url) for url, title in pages.items()])

    def _summary(self, course: _Course) -> str:
        where = course.record["category"] if course.record else "bölüm programı dışında"
        return f"{course.code} — {course.name} | {where} | {self._instructors(course)}"

    def _instructors(self, course: _Course) -> str:
        if not course.sections:
            return f"{self.term}: bu dönem açılmamış"
        return f"{self.term} hocaları: {instructors_line(course.sections)}"

    def _courses_of(self, staff_name: str) -> str:
        return _teaching(self._catalog.timetable.sections_of_teacher(staff_name))

    def _citations(self, *keys: str) -> list[Citation]:
        return [self._catalog.sources[key] for key in keys if key in self._catalog.sources]


def _course_index(catalog: Catalog) -> dict[str, _Course]:
    """Ders koduna göre: bölüm programındaki kayıt (Türkçe ad) ve programdaki şubeler."""
    courses: dict[str, _Course] = {}
    for record in catalog.courses:
        code = record["code"].replace(" ", "").upper()
        courses[code] = _Course(code=code, name=record["name"], record=record)
    for section in catalog.timetable.sections:
        course = courses.setdefault(section.code, _Course(code=section.code, name=section.name))
        course.sections.append(section)
    for course in courses.values():
        names = f"{course.name} {' '.join(s.name for s in course.sections)}"
        course.words = frozenset(stem(token) for token in normalize(names).split())
    return courses


def _codes_in(text: str) -> list[str]:
    return [(letters + number).upper() for letters, number in _COURSE_CODE.findall(text)]


def _prefix(code: str) -> str:
    return re.sub(r"\d.*", "", code).lower()


def _same(query: str, name: str) -> bool:
    """Sorulan ad ("Yazıcı", "ali yazıcı") kayıttaki adla ("Prof. Dr. Ali YAZICI") uyuşuyor mu."""
    asked = name_tokens(query)
    return bool(asked) and (set(asked) <= set(name_tokens(name)) or same_person(query, name))


def _teaching(sections: list[Section]) -> str:
    """"CMPE113 Computer Programming I (Şube 01, 02); FE302 … (Şube 06)"."""
    by_course: dict[tuple[str, str], list[str]] = {}
    for section in sections:
        by_course.setdefault((section.code, section.name), []).append(section.number)
    return "; ".join(
        f"{code} {name} (Şube {', '.join(numbers)})" for (code, name), numbers in by_course.items()
    )
