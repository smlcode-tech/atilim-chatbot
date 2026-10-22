import pytest

from atilim_assistant.chat.tools import _MAX_DOCUMENT_CHARS, Tools
from atilim_assistant.domain import Citation, Document
from atilim_assistant.ingestion.parsers.departments.software_engineering.ders_programi import (
    Section,
    Timetable,
)
from atilim_assistant.retrieval.catalog import Catalog, CatalogStore
from tests.conftest import FakeRetriever

TERM = "2026-2027 Güz Dönemi"


def _course(code: str, name: str, **fields) -> dict:
    return {
        "code": code, "name": name, "category": "Zorunlu Dersler", "theory": 3, "practice": 0,
        "lab": 0, "credit": 3.0, "akts": 6.0, "precondition": "", "content": "", **fields,
    }


def _member(name: str, research: str = "") -> dict:
    return {"name": name, "role": "", "employment": "", "phone": "", "email": "",
            "education": "", "research": research}


@pytest.fixture
def tools(tmp_path, staff_documents) -> Tools:
    store = CatalogStore(tmp_path / "catalog.json")
    store.replace(
        "courses",
        [
            _course("MATH276", "Diferansiyel Denklemler", precondition="MATH152"),
            _course("SE212", "İnsan Bilgisayar Etkileşimi"),
            _course("CMPE113", "Bilgisayar Programlama I"),
        ],
        Citation("Dersler", "https://example.edu/dersler"),
    )
    store.replace(
        "staff",
        [_member("Prof. Dr. Ali YAZICI", "Algoritmalar"), _member("Doç. Dr. Erhan GÖKÇAY")],
        Citation("Akademik Personel", "https://example.edu/personel"),
    )
    store.replace(
        "admin_staff",
        [{"name": "Yasemin KURT", "title": "Bölüm Sekreteri", "phone": "+90 (312) 586 8398",
          "email": "yasemin.kurt@example.edu"}],
        Citation("İdari Personel", "https://example.edu/idari-personel"),
    )
    store.replace_timetable(
        Timetable(
            TERM,
            (
                Section("CMPE113", "01", "Computer Programming I", ("Ali Yazıcı",)),
                Section("MATH151", "01", "Calculus I", ("Fatma Eroğlu",)),
                Section("MATH151", "02", "Calculus I", ("Serdar Ay",)),
                Section("MATH276", "01", "Differential Equations", ("Emel Kavgacı",)),
            ),
        ),
        Citation(f"Ders Programı — {TERM}", "https://example.edu/program"),
    )
    return Tools(store.load(), FakeRetriever(staff_documents))


def test_catalog_store_keeps_each_record_type_and_its_source(tools):
    assert tools.term == TERM
    result = tools.ders_detayi("MATH276")
    assert "Ön koşul: MATH152" in result.text
    assert "2026-2027 Güz Dönemi hocaları: Emel Kavgacı" in result.text
    assert [c.title for c in result.citations] == ["Dersler", f"Ders Programı — {TERM}"]


def test_course_search_by_prefix_lists_every_course_with_its_teachers(tools):
    text = tools.ders_ara("MATH").text
    assert "MATH151 — Calculus I | bölüm programı dışında" in text
    assert "Fatma Eroğlu (Şube 01); Serdar Ay (Şube 02)" in text
    assert "MATH276 — Diferansiyel Denklemler | Zorunlu Dersler" in text
    assert "SE212" not in text


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("diferansiyel", "MATH276"),  # bölüm programındaki Türkçe ad
        ("differential equations", "MATH276"),  # ders programındaki İngilizce ad
        ("MATF276", "MATH276"),  # yazım hatası
        ("se 212", "SE212"),
    ],
)
def test_course_search_matches_codes_and_names_in_either_language(tools, query, expected):
    assert tools.ders_ara(query).text.startswith(expected)


def test_course_not_offered_this_term_says_so(tools):
    assert "bu dönem açılmamış" in tools.ders_detayi("SE212").text


def test_teacher_courses_are_found_by_surname_across_the_university(tools):
    assert "Ali Yazıcı: CMPE113 Computer Programming I (Şube 01)" in tools.hocanin_dersleri("Yazıcı").text
    assert "Fatma Eroğlu" in tools.hocanin_dersleri("fatma eroğlu").text
    assert "yok" in tools.hocanin_dersleri("Bilinmeyen Kişi").text


def test_department_roster_lists_each_members_courses_this_term(tools):
    # "Bu hocalardan hangileri MATH dersi veriyor?" sorusu bu listeden süzülür.
    text = tools.bolum_kadrosu().text
    assert "Prof. Dr. Ali YAZICI | Araştırma: Algoritmalar | Bu dönem dersleri: CMPE113" in text
    assert "Doç. Dr. Erhan GÖKÇAY | Bu dönem dersleri: yok" in text


def test_staff_details_include_this_terms_courses(tools):
    text = tools.personel_bilgisi("ali yazıcı").text
    assert text.startswith("Prof. Dr. Ali YAZICI")
    assert f"{TERM} dersleri: CMPE113" in text


def test_staff_details_cover_administrative_staff(tools):
    result = tools.personel_bilgisi("yasemin kurt")
    assert result.text == (
        "Yasemin KURT (idari personel)\nUnvan: Bölüm Sekreteri\n"
        "Telefon: +90 (312) 586 8398\nE-posta: yasemin.kurt@example.edu"
    )
    assert [c.title for c in result.citations] == ["İdari Personel"]


def test_document_search_returns_page_text_with_citations(tools, staff_source):
    result = tools.belge_ara("bölüm başkanı")
    assert "Görev: Bölüm Başkanı" in result.text
    assert [c.url for c in result.citations] == [staff_source.url]


def test_document_search_skips_documents_that_overflow_the_context_budget():
    def document(id_: str, size: int) -> Document:
        return Document(
            id=id_, source_id="s", source_title="Sayfa", url="https://example.edu",
            unit="", category="", title=id_, text=id_ * size,
        )

    big = _MAX_DOCUMENT_CHARS * 2 // 3
    retrieved = [document("A", big), document("B", big), document("C", 100)]
    result = Tools(Catalog.empty(), FakeRetriever(retrieved)).belge_ara("staj")

    # İkinci büyük belge bütçeyi aşar ve atlanır; arama sürer, sonraki kısa belge yine sığar.
    assert "A" * big in result.text
    assert "B" * big not in result.text
    assert "C" * 100 in result.text


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("yok_boyle_arac", "{}", "Bilinmeyen araç"),
        ("ders_ara", "{bozuk", "Geçersiz argüman"),
        ("ders_ara", '{"yanlis": "x"}', "Geçersiz argüman"),
    ],
)
def test_bad_tool_calls_are_explained_to_the_model(tools, name, arguments, message):
    assert tools.run(name, arguments).text.startswith(message)


class _BrokenRetriever(FakeRetriever):
    def retrieve(self, query):
        raise RuntimeError("Voyage: 429 Too Many Requests")


def test_a_failing_tool_is_reported_to_the_model_instead_of_raising():
    tools = Tools(Catalog.empty(), _BrokenRetriever([]))
    result = tools.run("belge_ara", '{"sorgu": "staj"}')
    assert result.text.startswith("belge_ara şu anda çalışmıyor")


def test_an_empty_catalog_answers_without_failing(staff_documents):
    tools = Tools(Catalog.empty(), FakeRetriever(staff_documents))
    assert "eşleşen ders yok" in tools.ders_ara("MATH").text
    assert tools.bolum_kadrosu().text == "Kadro bilgisi yok."
