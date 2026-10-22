import pytest

from atilim_assistant.domain import Source
from atilim_assistant.ingestion.parsers.departments.software_engineering import (
    academic_staff,
    ders_programi,
    dersler,
)
from atilim_assistant.ingestion.parsers.departments.software_engineering.ders_programi import (
    Meeting,
    Section,
    Timetable,
)
from tests.conftest import FIXTURES


def _table(table_id: str, rows: list[dict]) -> dict:
    return {"id": table_id, "data_rows": rows}


def _response() -> dict:
    return {
        "dbiAccessorRes": {
            "tables": [
                _table(
                    "subjects",
                    [
                        {"id": "s1", "name": "SE221-SEC-01-Software Requirements Engineering"},
                        {"id": "s2", "name": "MATH 151-SEC-02-Calculus I"},
                        {"id": "s3", "name": "TIP"},
                    ],
                ),
                _table(
                    "teachers",
                    [
                        {"id": "t1", "short": "Ayşe Örnek"},
                        {"id": "t2", "short": "Staff"},
                        {"id": "t3", "short": "Mehmet Deneme"},
                    ],
                ),
                _table(
                    "lessons",
                    [
                        # Aynı şube haftada iki kez geçer.
                        {"id": "l1", "subjectid": "s1", "teacherids": ["t1"], "durationperiods": 3},
                        {"id": "l2", "subjectid": "s1", "teacherids": ["t1"], "durationperiods": 1},
                        {"id": "l3", "subjectid": "s2", "teacherids": ["t2", "t3"], "durationperiods": 2},
                        {"id": "l4", "subjectid": "s3", "teacherids": ["t1"], "durationperiods": 1},
                    ],
                ),
                _table(
                    "cards",
                    [
                        # Perşembe oturumu Salı'dan önce gelse de çıktıda güne göre dizilir.
                        {"id": "c1", "lessonid": "l2", "days": "000100", "period": "2", "classroomids": []},
                        {"id": "c2", "lessonid": "l1", "days": "010000", "period": "1", "classroomids": ["r1"]},
                        {"id": "c3", "lessonid": "l3", "days": "100000", "period": "2", "classroomids": ["r2"]},
                        # Programa yerleştirilmemiş kart.
                        {"id": "c4", "lessonid": "l3", "days": "", "period": "", "classroomids": []},
                    ],
                ),
                _table(
                    "periods",
                    [
                        {"id": str(n), "period": str(n), "starttime": f"{8 + n}:30", "endtime": f"{9 + n}:20"}
                        for n in range(1, 4)
                    ],
                ),
                _table(
                    "days",
                    [
                        {"id": str(i), "name": name}
                        for i, name in enumerate(["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
                    ],
                ),
                _table("classrooms", [{"id": "r1", "name": "Müh. 1025H"}, {"id": "r2", "name": " C001"}]),
            ]
        }
    }


def test_parse_links_course_codes_to_teachers_and_skips_placeholders():
    timetable = ders_programi.parse("2026-2027 Güz Dönemi", _response())
    assert timetable.sections == (
        Section(
            "MATH151", "02", "Calculus I", ("Mehmet Deneme",),
            (Meeting("Pazartesi", "10:30", "12:20", "C001"),),
        ),
        Section(
            "SE221", "01", "Software Requirements Engineering", ("Ayşe Örnek",),
            (
                Meeting("Salı", "9:30", "12:20", "Müh. 1025H"),
                Meeting("Perşembe", "10:30", "11:20", ""),
            ),
        ),
    )


def test_schedule_lines_give_each_section_its_days_times_and_rooms():
    sections = ders_programi.parse("2026-2027 Güz Dönemi", _response()).sections_of_course("SE221")
    assert ders_programi.schedule_lines(sections) == [
        "Şube 01 (Ayşe Örnek): Salı 9:30–12:20 (Müh. 1025H), Perşembe 10:30–11:20"
    ]
    assert ders_programi.meetings_line(()) == "programda gün/saat yok"


@pytest.mark.parametrize(
    ("teacher", "staff", "same"),
    [
        ("Ali Yazıcı", "Prof. Dr. Ali YAZICI", True),
        ("Sacit Uluırmak", "Öğr. Gör. Nimet Sacit ULUIRMAK", True),
        ("Guler Kalem", "Dr. Öğr. Üyesi Güler KALEM", True),
        ("Mehmet Bulut", "Dr. Öğr. Üyesi Onur BULUT", False),
        ("BULUT", "Dr. Öğr. Üyesi Onur BULUT", False),
    ],
)
def test_same_person_matches_names_across_title_case_and_middle_names(teacher, staff, same):
    assert ders_programi.same_person(teacher, staff) is same


def test_instructors_line_groups_sections_by_teacher():
    sections = [
        Section("MATH151", "01", "Calculus I", ("Fatma Eroğlu",)),
        Section("MATH151", "02", "Calculus I", ("Fatma Eroğlu",)),
        Section("MATH151", "03", "Calculus I", ("Serdar Ay",)),
    ]
    assert ders_programi.instructors_line(sections[:2]) == "Fatma Eroğlu"
    assert ders_programi.instructors_line(sections) == "Fatma Eroğlu (Şube 01, 02); Serdar Ay (Şube 03)"


_TIMETABLE = Timetable(
    term="2026-2027 Güz Dönemi",
    sections=(
        Section(
            "SE221", "01", "Software Requirements Engineering", ("Ayşe Örnek",),
            (Meeting("Salı", "09:30", "12:20", "Müh. 1025H"),),
        ),
    ),
)


def test_staff_answers_list_the_courses_each_member_teaches(monkeypatch, staff_source):
    monkeypatch.setattr(ders_programi, "current", lambda: _TIMETABLE)
    html = (FIXTURES / "academic_staff.html").read_text(encoding="utf-8")
    content = academic_staff.parse(html, staff_source)
    answers = {a.questions[0]: a.answer for a in content.prepared_answers}
    member = next(q for q in answers if q.endswith("ÖRNEK hangi dersleri veriyor?"))
    assert "SE221 Software Requirements Engineering (Şube 01)" in answers[member]
    assert "Ayşe ÖRNEK" in answers["Hangi hocalar hangi dersleri veriyor?"]
    assert not any("DENEME hangi dersleri" in q for q in answers)


def test_course_documents_name_the_instructor(monkeypatch):
    monkeypatch.setattr(ders_programi, "current", lambda: _TIMETABLE)
    card = (
        '<div class="lesson_card" data-lesson-data=\'{"code": "SE221", '
        '"name": "Yazılım Gereksinim Mühendisliği", "akts": 6}\'></div>'
    )
    html = (
        f'<div class="detail-container"><div id="required_les">{card}</div>'
        '<div id="technical_lessons"></div><div id="general_lessons"></div></div>'
    )
    source = Source("se-dersler", "Dersler", "https://example.edu", "Test", "ders", dersler.parse)
    content = dersler.parse(html, source)
    course = next(a for a in content.prepared_answers if a.answer.startswith("SE221 —"))
    assert "Öğretim elemanı (2026-2027 Güz Dönemi): Ayşe Örnek" in course.answer
    assert "SE221 dersini kim veriyor, hocası kim?" in course.questions
    assert "Şube 01 (Ayşe Örnek): Salı 09:30–12:20 (Müh. 1025H)" in course.answer
    assert "SE221 dersi hangi gün, saat kaçta?" in course.questions


def test_courses_sharing_a_name_get_patterns_of_their_own(monkeypatch):
    """Adla sorulan kalıp tek bir derse götürmeli; yoksa hep ilk dersin yanıtı verilir."""
    monkeypatch.setattr(ders_programi, "current", lambda: None)
    cards = "".join(
        f'<div class="lesson_card" data-lesson-data=\'{{"code": "{code}", '
        f'"name": "İş Sağlığı ve Güvenliği", "akts": 2}}\'></div>'
        for code in ("FE301", "IE443")
    )
    html = (
        f'<div class="detail-container"><div id="required_les">{cards}</div>'
        '<div id="technical_lessons"></div><div id="general_lessons"></div></div>'
    )
    source = Source("se-dersler", "Dersler", "https://example.edu", "Test", "ders", dersler.parse)
    content = dersler.parse(html, source)

    by_code = {a.answer[:5]: a.questions for a in content.prepared_answers if " — " in a.answer}
    assert "İş Sağlığı ve Güvenliği (FE301) dersi hakkında bilgi" in by_code["FE301"]
    assert "İş Sağlığı ve Güvenliği (IE443) dersi hakkında bilgi" in by_code["IE443"]
    patterns = [question for questions in by_code.values() for question in questions]
    assert not any(q.startswith("İş Sağlığı ve Güvenliği dersi") for q in patterns)
