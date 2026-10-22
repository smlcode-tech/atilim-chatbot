"""Lisans Programı Müfredat sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container):
  - Her yarıyıl bir h3 başlığı ve ardından bir tablo içerir.
  - Tablodaki her ders satırında `data-lesson-data` JSON özniteliği bulunur;
    bu öznitelik ders kodu, adı, Türkçe/İngilizce içerik açıklaması,
    teorik/uygulama saati ve AKTS bilgilerini taşır.
"""

import json
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for
from atilim_assistant.text import collapse_whitespace, markdown_table

# Yarıyıl başlığındaki sıra sayısı ("5. Yarıyıl" → 5).
_SEMESTER_NUMBER = re.compile(r"(\d+)\.\s*Yarıyıl")
# Sınıflar yazıyla da sorulur ("üçüncü sınıf dersleri"); kalıplar iki biçimle de üretilir.
_ORDINALS = {1: "Birinci", 2: "İkinci", 3: "Üçüncü", 4: "Dördüncü", 5: "Beşinci", 6: "Altıncı"}


@dataclass(frozen=True, slots=True)
class _Course:
    """Müfredat tablosundaki bir satır. Seçmeli ders yuvalarında `code` boştur."""

    code: str
    name: str
    theory: int
    practice: int
    akts: float


@dataclass(frozen=True, slots=True)
class _Semester:
    """Bir yarıyıl; `total_akts` sayfanın kendi yazdığı toplamdır, hesaplanmaz."""

    name: str
    courses: list[_Course] = field(default_factory=list)
    total_akts: float | None = None


def parse(html: str, source: Source) -> SourceContent:
    """Müfredattan yarıyıl ve sınıf düzeyinde belgeler ve hazır yanıtlar. Bu sayfanın
    katkısı derslerin hangi yarıyılda okunduğudur; ders ayrıntıları "Dersler" sayfasından gelir."""
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
    all_parts = [f"{source.unit} Lisans Programı Müfredatı"]
    for sem in semesters:
        all_parts.append(f"{sem.name}:\n{_courses_table(sem.courses)}")
        if sem.total_akts:
            all_parts.append(_total_line(sem))
    full_roster = "\n\n".join(all_parts)
    documents.append(doc_for(source, "mufredat-ozet", source.title, full_roster))

    # Toplamı model ders listesinden kendisi hesaplamaya kalkışmasın (seçmeli yuvaları atlayıp
    # yanlış sonuç verir); sayfadaki yarıyıl toplamları kısa, ayrı bir belgede verilir. Uzun
    # müfredat özeti bağlam bütçesine çoğu zaman sığmaz.
    totals = [sem.total_akts for sem in semesters]
    if all(totals):
        totals_table = markdown_table(
            ["Yarıyıl", "AKTS"], [[sem.name, f"{sem.total_akts:g}"] for sem in semesters]
        )
        totals_text = (
            f"{source.unit} lisans programı AKTS toplamları (müfredat sayfasına göre):\n"
            f"{totals_table}\n\nSekiz yarıyılın toplamı: {sum(totals):g} AKTS"
        )
        documents.append(doc_for(source, "akts-toplamlari", "Müfredat AKTS Toplamları", totals_text))

    # Hazır yanıt: genel müfredat sorusu
    answers.append(
        answer_for(
            source,
            [
                f"{source.unit} müfredatı nedir?",
                "Yazılım mühendisliği bölümünde hangi dersler var?",
                "Lisans programı dersleri neler?",
                "SE bölümü müfredatı",
                "Ders planı, öğretim planı nedir?",
                "Dört yıl boyunca hangi dersleri alacağım?",
                "Yarıyıllara göre ders dağılımı nasıl?",
            ],
            full_roster,
        )
    )

    # Her yarıyıl için ayrı belge ve hazır yanıt
    for sem in semesters:
        sem_parts = [
            f"{source.unit} {sem.name}{_year_label(sem.name)} dersleri:\n"
            + _courses_table(sem.courses, hours=True)
        ]
        if sem.total_akts:
            sem_parts.append(_total_line(sem))
        sem_text = "\n\n".join(sem_parts)
        slug = sem.name.lower().replace(". ", "-").replace(" ", "-")
        documents.append(doc_for(source, slug, f"{sem.name} Dersleri", sem_text))
        answers.append(
            answer_for(
                source,
                [
                    f"{sem.name} dersleri neler?",
                    f"Yazılım mühendisliği {sem.name.lower()} hangi dersleri alıyorum?",
                    f"{sem.name}da hangi dersler okunuyor, görülüyor?",
                    f"{sem.name}{_year_label(sem.name)} dersleri neler?",
                ],
                sem_text,
            )
        )

    # Öğrenciler "3. sınıf dersleri" diye sorar; sayfa ise yalnızca yarıyıl kullanır. Her sınıf
    # için iki yarıyılı birleştiren belge olmazsa arama "3." sayısına bakıp 3. yarıyılı getirir.
    years: dict[int, list[_Semester]] = {}
    for sem in semesters:
        number = _semester_number(sem.name)
        if number:
            years.setdefault((number + 1) // 2, []).append(sem)
    for year, year_semesters in sorted(years.items()):
        year_parts = [f"{source.unit} {year}. sınıf dersleri:"]
        for sem in year_semesters:
            year_parts.append(f"{sem.name}{_year_label(sem.name)}:\n{_courses_table(sem.courses)}")
            if sem.total_akts:
                year_parts.append(_total_line(sem))
        year_text = "\n\n".join(year_parts)
        documents.append(doc_for(source, f"{year}-sinif", f"{year}. Sınıf Dersleri", year_text))
        answers.append(
            answer_for(
                source,
                [
                    f"{year}. sınıf dersleri neler?",
                    f"{_ORDINALS[year]} sınıf dersleri neler?",
                    f"Yazılım mühendisliği {year}. sınıfta hangi dersleri alıyorum?",
                    f"{year}. sınıfta hangi dersler okunuyor, görülüyor?",
                    f"{_ORDINALS[year]} sınıfta hangi dersler okunuyor, görülüyor?",
                    f"{year}. sınıf güz ve bahar dönemi dersleri",
                ],
                year_text,
            )
        )

    # Ders başına belge burada üretilmez: "Dersler" sayfası aynı dersleri kredi ve ön koşul
    # bilgisiyle birlikte verir. İkisi birden indekslenince aynı soru kalıbı iki yanıta düşer ve
    # kopyalar sınırlı bağlamda yer kaplar. Dersin yarıyılı yukarıdaki yarıyıl belgelerindedir.

    return SourceContent(documents=documents, prepared_answers=answers)


def _semester_number(name: str) -> int | None:
    """Başlıktaki yarıyıl numarası; numarasız başlıkta None."""
    match = _SEMESTER_NUMBER.match(name)
    return int(match.group(1)) if match else None


def _year_label(semester_name: str) -> str:
    """"5. Yarıyıl" → " (3. sınıf güz dönemi)"; numarasız başlıklarda boş."""
    number = _semester_number(semester_name)
    if not number:
        return ""
    term = "güz" if number % 2 else "bahar"
    return f" ({(number + 1) // 2}. sınıf {term} dönemi)"


def _extract_semesters(container) -> list[_Semester]:
    """Her h3 başlığı ve ardından gelen tablo bir yarıyıldır. Dersi olmayan başlıklar (sayfadaki
    başka başlıklar) yarıyıl sayılmaz."""
    semesters = []
    for h3 in container.find_all("h3"):
        name = collapse_whitespace(h3.get_text())
        table = h3.find_next("table")
        courses = []
        total_akts = None
        if table:
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if not cells:
                    continue
                texts = [collapse_whitespace(cell.get_text()) for cell in cells]
                # Sayfanın kendi yarıyıl toplamı: ["Toplam", teorik, uygulama, akts]
                if texts[0] == "Toplam":
                    total_akts = _number(texts[-1])
                    continue
                link = cells[0].find("a", class_="lesson_card")
                if not link:
                    # Kodsuz satırlar seçmeli ders yuvalarıdır ("Alan Seçmeli" vb.); atlanırsa
                    # son sınıf listeleri eksik ve AKTS toplamları yanlış görünür.
                    if len(texts) == 5 and texts[1]:
                        courses.append(
                            _Course(
                                code="",
                                name=texts[1],
                                theory=int(_number(texts[2]) or 0),
                                practice=int(_number(texts[3]) or 0),
                                akts=_number(texts[4]) or 0.0,
                            )
                        )
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
                    )
                )
        if courses:
            semesters.append(_Semester(name=name, courses=courses, total_akts=total_akts))
    return semesters


def _number(text: str) -> float | None:
    """Tablo hücresindeki sayı; Türkçe ondalık virgülü ("7,5") de okunur. Sayı değilse None."""
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _courses_table(courses: list[_Course], hours: bool = False) -> str:
    """Yarıyıl derslerinin tablosu; `hours` ile teorik ve uygulama saatleri de yazılır. Kodsuz
    seçmeli yuvalarda kod hücresi "—" olur. Tablodan sonra gelen metin boş satırla ayrılmalıdır:
    Markdown'da bitişik satır tabloya katılır."""
    if hours:
        return markdown_table(
            ["Kod", "Ders", "Teorik", "Uygulama", "AKTS"],
            [[c.code, c.name, c.theory, c.practice, f"{c.akts:g}"] for c in courses],
        )
    return markdown_table(["Kod", "Ders", "AKTS"], [[c.code, c.name, f"{c.akts:g}"] for c in courses])


def _total_line(sem: _Semester) -> str:
    """Yarıyıl toplamı satırı; "sayfada belirtilen" ibaresi modelin toplamı kendisi
    yeniden hesaplamaya kalkışmamasına yardım eder."""
    return f"Yarıyıl toplamı (sayfada belirtilen): {sem.total_akts:g} AKTS" if sem.total_akts else ""
