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
    meetings_line,
    name_tokens,
    same_person,
    schedule_lines,
    teaching_line,
)
from atilim_assistant.retrieval.catalog import SECTIONS, Catalog
from atilim_assistant.text import FILLER_WORDS, correct_course_codes, normalize, stem

# Tek bir araç sonucunun sınırları: model bağlamı ve dakikalık token kotası sınırlıdır.
# "MATH" gibi geniş bir önek yüzlerce ders döndürür; ilk 30'u ve kalan sayısı yeter.
_MAX_COURSES = 30
# belge_ara'nın modele verdiği toplam metin; birkaç ilgili parça sığar, sayfanın tamamı sığmaz.
# Groq ücretsiz katmanı dakikada 8000 token kabul eder; bir soru birkaç model turu sürdüğü için
# tek bir araç sonucu bunun küçük bir parçası olmalıdır. Bağlam sınırı yalnızca burada tutulur.
_MAX_DOCUMENT_CHARS = 6000
# bolum_kadrosu tüm kadroyu tek sonuçta verir; araştırma konusu kişi başına kırpılmazsa liste
# kotayı tek başına bitirir. Ayrıntı gerekirse model personel_bilgisi'ni çağırır.
_MAX_RESEARCH_CHARS = 100

logger = logging.getLogger(__name__)

# Normalleştirilmiş (küçük harf) metindeki ders kodu: "se212", "se 212", "math151a".
_COURSE_CODE = re.compile(r"\b([a-z]{2,5}) ?(\d{3}[a-z]?)\b")
# Ders adında aranacak en kısa sözcük; "ve", "of" gibi kısa sözcükler her derse uyardı.
_MIN_WORD = 3


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Bir aracın modele döndürdüğü metin ve yanıtta kaynak olarak gösterilecek sayfalar.

    Kaynaklar metinden ayrı taşınır: model yalnızca metni görür, kaynakları `ChatService`
    toplar. Böylece kaynak listesi modelin yazdığına değil, gerçekten sorgulanan veriye dayanır.
    """

    text: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class _Course:
    """Ders arama dizinindeki bir ders.

    İki kaynağı birleştirir: bölüm müfredatındaki kayıt (`record`: kredi, AKTS, içerik; yalnızca
    Yazılım Mühendisliği dersleri için var) ve ders programındaki şubeler (`sections`: bu dönem
    kim veriyor; tüm üniversite). Bölüm dışı derslerde `record` boştur. `words`, ad aramasında
    her sorguda yeniden hesaplanmasın diye bir kez çıkarılan kök sözcüklerdir.
    """

    code: str
    name: str
    record: dict | None = None
    sections: list[Section] = field(default_factory=list)
    words: frozenset[str] = frozenset()


def _function(name: str, description: str, **parameters: str) -> dict:
    """OpenAI uyumlu araç tanımı üretir; her parametre zorunlu bir metindir.

    Tanımlar elle JSON şeması olarak yazılsaydı her araç için aynı iç içe yapı tekrarlanırdı.
    Araçların hepsi metin aldığı için tip seçeneği gerekmez.
    """
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


# Modele sunulan araçlar. Adlar ve açıklamalar Türkçedir çünkü model kullanıcının Türkçe
# sorusunu bu açıklamalarla eşleştirerek araç seçer. Açıklamalardaki kapsam bilgisi ("tüm
# üniversite", "Yazılım Mühendisliği Bölümü") modelin yanlış araçta boşuna aramasını önler.
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
        "Bir dersin kredi, AKTS, haftalık saat, ön koşul, içerik ve bu dönemki şubelerini "
        "getirir: her şubenin hocası, günü, saati ve dersliği.",
        kod="Ders kodu, ör. SE212",
    ),
    _function(
        "hocanin_dersleri",
        "Bir öğretim elemanının bu dönem ders programında verdiği dersler, gün, saat ve "
        "derslikleriyle (tüm üniversite).",
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
    """`DEFINITIONS`'taki araçların uygulaması.

    Yapılandırılmış sorular (ders, hoca, kadro) katalogdan kesin olarak yanıtlanır; yalnızca
    serbest metin konular (staj, Erasmus, SSS) `retriever` ile belge aramasına gider. Metin
    araması "bu dönem MATH veren hocalar" gibi bir listeyi eksiksiz getiremezdi.

    `retriever`: üretimde `HybridRetriever`, testlerde `FakeRetriever`. `retrieve`,
    `similar_questions` ve `course_codes` sağlayan her nesne kullanılabilir.
    """

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
        """Ders programının dönemi; sistem talimatı ve araç sonuçları hangi dönemi kapsadığını
        söylesin diye dışarı açılır."""
        return self._catalog.timetable.term

    def correct(self, text: str) -> str:
        """Tek harfle yanlış yazılmış ders kodunu düzeltir ("MATF276" → "MATH276").

        Bilinen kodlar hem katalogdan hem belge indeksinden toplanır: bazı kodlar yalnızca bölüm
        sayfalarında geçer, yalnızca katalogla düzeltilselerdi yanlış koda çevrilebilirlerdi.
        """
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
        """Kod, kod öneki ya da ad sözcükleriyle ders arar; her dersin bu dönemki hocalarını da
        verir ki "X dersini kim veriyor?" tek çağrıda yanıtlansın.

        Sıralama önceliği: tam kod eşleşmesi, sonra önek eşleşmesi, sonra ortak sözcük sayısı.
        Böylece "SE212" sorgusunda SE212 her zaman ilk sırada çıkar, adı benzeyen dersler
        arkadan gelir. Önek olarak tanınan sözcükler ("math") ad aramasına ayrıca katılmaz;
        aynı sözcük iki kez puan getirmez.
        """
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
        """Tek bir dersin müfredat ayrıntısı ve bu dönemki hocaları.

        Bölüm dışı derslerde müfredat kaydı yoktur; bu durumda bunu açıkça yazar. Böylece model
        kredi bilgisinin eksikliğini "ders yok" diye yorumlamaz.
        """
        # Kod kalıba uymazsa (beklenmedik biçim) ham değer denenir; dizinde yoksa "bulunamadı" döner.
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
        if course.sections:
            lines += [f"{self.term} ders saatleri:", *schedule_lines(course.sections)]
        return ToolResult("\n".join(lines), self._citations("courses", SECTIONS))

    def hocanin_dersleri(self, ad: str) -> ToolResult:
        """Bir öğretim elemanının bu dönem verdiği dersler; ders programı üzerinden, tüm
        üniversitede.

        Ada uyan herkes listelenir: "Yılmaz" birden çok kişiye uyabilir ve hangisinin
        kastedildiğine model konuşmadan karar verir. Bölüm kadrosunda olmayan hocalar (ör. ortak
        dersleri veren Matematik hocaları) yalnızca bu araçla bulunur.
        """
        teachers = sorted(
            {t for s in self._catalog.timetable.sections for t in s.teachers if _same(ad, t)}
        )
        if not teachers:
            return ToolResult(f"{self.term} ders programında '{ad}' adlı öğretim elemanı yok.")
        lines = []
        for teacher in teachers:
            sections = self._catalog.timetable.sections_of_teacher(teacher)
            lines.append(f"{teacher}: {teaching_line(sections)}")
            # "X hoca salı günü derste mi?" gibi sorular için her şubenin günü ve saati.
            lines += [f"  {s.code} Şube {s.number}: {meetings_line(s.meetings)}" for s in sections]
        return ToolResult(f"{self.term} ders programı:\n" + "\n".join(lines), self._citations(SECTIONS))

    def bolum_kadrosu(self) -> ToolResult:
        """Bölüm kadrosunun tamamı, her hocanın bu dönemki dersleriyle birlikte, tek sonuçta.

        "Bu hocalardan hangileri MATH dersi veriyor?" gibi süzme soruları için tasarlandı: model
        hocaları tek tek sorgulasaydı her biri ayrı bir tur olur ve tur sınırına ya da dakikalık
        kotaya takılırdı. Satırlar bu yüzden kısa tutulur (bkz. `_MAX_RESEARCH_CHARS`).
        """
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
        """Bölümdeki bir kişinin tüm bilgileri: akademik kadro ya da idari personel.

        İki liste birlikte aranır çünkü kullanıcı "bölüm sekreterinin telefonu" ile "hocanın
        e-postası"nı aynı biçimde sorar; model kişinin hangi listede olduğunu bilemez. Bulunamazsa
        model hocanin_dersleri'ne yönlendirilir: kişi başka bölümden olabilir.
        """
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
        # Yalnızca bilgisi kullanılan sayfalar kaynak gösterilir; idari personel sorusunda
        # akademik kadro sayfası kaynak değildir.
        keys = ["staff", SECTIONS] if members else []
        return ToolResult("\n\n".join(blocks), self._citations(*keys, *(["admin_staff"] if admins else [])))

    def belge_ara(self, sorgu: str) -> ToolResult:
        """Bölüm sayfalarında karma (vektör + BM25) arama; katalogda yapılandırılmamış konular
        için. Her parçanın başına sayfa adı eklenir ki model bilgiyi hangi sayfadan aldığını
        bilsin."""
        documents: list[Document] = []
        used = 0
        for document in self._retriever.retrieve(sorgu):
            # Sığmayan parça atlanır ama döngü sürer: sonraki, daha kısa ve yine ilgili bir
            # parça hâlâ sığabilir.
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
        """ders_ara sonucundaki tek satır: kod, ad, müfredattaki yeri, bu dönemki hocalar."""
        where = course.record["category"] if course.record else "bölüm programı dışında"
        return f"{course.code} — {course.name} | {where} | {self._instructors(course)}"

    def _instructors(self, course: _Course) -> str:
        """Dersin bu dönemki hocaları. Şubesi olmayan ders için "açılmamış" yazılır; boş
        bırakılsaydı model bunu "hoca bilgisi yok" sanabilirdi."""
        if not course.sections:
            return f"{self.term}: bu dönem açılmamış"
        return f"{self.term} hocaları: {instructors_line(course.sections)}"

    def _courses_of(self, staff_name: str) -> str:
        """Personel sayfasındaki adla ders programındaki dersler; adların iki kaynakta farklı
        yazılışını `sections_of_teacher` eşleştirir."""
        return teaching_line(self._catalog.timetable.sections_of_teacher(staff_name))

    def _citations(self, *keys: str) -> list[Citation]:
        """Katalog bölümlerinin kaynak sayfaları. Ingest'te alınamayan bölümün kaynağı yoktur;
        o bölüm sessizce atlanır, olmayan bir sayfa gösterilmez."""
        return [self._catalog.sources[key] for key in keys if key in self._catalog.sources]


def _course_index(catalog: Catalog) -> dict[str, _Course]:
    """Ders koduna göre: bölüm programındaki kayıt (Türkçe ad) ve programdaki şubeler.

    Dizin açılışta bir kez kurulur; katalog çalışırken değişmez ve her araç çağrısında iki
    kaynağı yeniden birleştirmek gereksiz olurdu. Ad sözcükleri iki kaynaktan birlikte alınır:
    müfredatta Türkçe, ders programında İngilizce ad olabilir, iki dille de bulunabilsin.
    """
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
    """Metindeki ders kodları, dizindeki biçimde ("se 212" → "SE212")."""
    return [(letters + number).upper() for letters, number in _COURSE_CODE.findall(text)]


def _prefix(code: str) -> str:
    """Kodun harf kısmı ("SE212" → "se"); "MATH dersleri" gibi önek aramaları için."""
    return re.sub(r"\d.*", "", code).lower()


def _same(query: str, name: str) -> bool:
    """Sorulan ad ("Yazıcı", "ali yazıcı") kayıttaki adla ("Prof. Dr. Ali YAZICI") uyuşuyor mu."""
    asked = name_tokens(query)
    return bool(asked) and (set(asked) <= set(name_tokens(name)) or same_person(query, name))
