import pytest

from atilim_assistant.ingestion.parsers.departments.software_engineering import academic_staff


def test_produces_roster_and_one_document_per_member(staff_documents):
    assert [document.id for document in staff_documents] == [
        "test-akademik-personel:kadro",
        "test-akademik-personel:prof-dr-ayse-ornek",
        "test-akademik-personel:ars-gor-isil-caliskan",
        "test-akademik-personel:ogr-gor-mehmet-deneme",
    ]


def test_member_document_contains_all_fields(staff_documents):
    assert staff_documents[1].title == "Prof. Dr. Ayşe ÖRNEK"
    assert staff_documents[1].text == (
        "Prof. Dr. Ayşe ÖRNEK — Test Bölümü akademik personeli\n"
        "Görev: Bölüm Başkanı\n"
        "Telefon: +90 (312) 586 8376\n"
        "Eğitim: Lisans, Yüksek Lisans: Orta Doğu Teknik Üniversitesi; "
        "Doktora: Waterloo Üniversitesi, Canada\n"
        "Araştırma Konuları: Algoritmalar, Veri Madenciliği, Yazılım Mühendisliği."
    )


def test_missing_fields_are_omitted_or_marked(staff_documents):
    assert staff_documents[2].text == (
        "Arş. Gör. Işıl ÇALIŞKAN — Test Bölümü akademik personeli\n"
        "Telefon: +90 (312) 586 80 00\n"
        "Araştırma Konuları: Sayfada belirtilmemiş"
    )


def test_section_heading_marks_employment_type(staff_documents):
    assert "Kadro: Yarı Zamanlı Öğretim Elemanları" in staff_documents[3].text
    assert "Kadro:" not in staff_documents[1].text


def test_roster_lists_every_member(staff_documents):
    assert staff_documents[0].text == (
        "Test Bölümü akademik kadrosu (3 kişi):\n"
        "- Prof. Dr. Ayşe ÖRNEK – Bölüm Başkanı\n"
        "- Arş. Gör. Işıl ÇALIŞKAN\n"
        "- Öğr. Gör. Mehmet DENEME – Yarı Zamanlı Öğretim Elemanları"
    )


def test_documents_carry_source_metadata(staff_documents, staff_source):
    for document in staff_documents:
        assert document.source_id == staff_source.id
        assert document.source_title == staff_source.title
        assert document.url == staff_source.url


def _answer_to(staff_answers, question):
    return next(answer for answer in staff_answers if question in answer.questions)


def test_each_member_gets_profile_research_contact_and_education_answers(staff_answers):
    name = "Prof. Dr. Ayşe ÖRNEK"
    assert _answer_to(staff_answers, f"{name} kimdir?").answer == (
        "**Prof. Dr. Ayşe ÖRNEK** — Test Bölümü akademik personeli\n"
        "\n"
        "- Görev: Bölüm Başkanı\n"
        "- Telefon: +90 (312) 586 8376\n"
        "- Eğitim: Lisans, Yüksek Lisans: Orta Doğu Teknik Üniversitesi; "
        "Doktora: Waterloo Üniversitesi, Canada\n"
        "- Araştırma Konuları: Algoritmalar, Veri Madenciliği, Yazılım Mühendisliği."
    )
    assert _answer_to(staff_answers, f"{name} araştırma konuları neler?").answer == (
        "**Prof. Dr. Ayşe ÖRNEK** — araştırma konuları: "
        "Algoritmalar, Veri Madenciliği, Yazılım Mühendisliği."
    )
    assert _answer_to(staff_answers, f"{name} telefon numarası nedir?").answer == (
        "**Prof. Dr. Ayşe ÖRNEK** — telefon: +90 (312) 586 8376. "
        "E-posta adresi için kaynak sayfaya bakabilirsin."
    )
    assert _answer_to(staff_answers, f"{name} hangi üniversiteden mezun?").answer == (
        "**Prof. Dr. Ayşe ÖRNEK** — eğitim: Lisans, Yüksek Lisans: Orta Doğu Teknik Üniversitesi; "
        "Doktora: Waterloo Üniversitesi, Canada"
    )


def test_answers_mark_fields_missing_from_the_page(staff_answers):
    name = "Arş. Gör. Işıl ÇALIŞKAN"
    assert _answer_to(staff_answers, f"{name} araştırma konuları neler?").answer == (
        "**Arş. Gör. Işıl ÇALIŞKAN** — araştırma konuları: Sayfada belirtilmemiş"
    )
    assert _answer_to(staff_answers, f"{name} eğitim bilgileri neler?").answer == (
        "**Arş. Gör. Işıl ÇALIŞKAN** — eğitim: Sayfada belirtilmemiş"
    )


def test_unit_answers_cover_roster_officers_and_employment_groups(staff_answers):
    assert _answer_to(staff_answers, "Test Bölümü akademik kadrosunda kimler var?").answer == (
        "Test Bölümü akademik kadrosu (3 kişi):\n"
        "- Prof. Dr. Ayşe ÖRNEK – Bölüm Başkanı\n"
        "- Arş. Gör. Işıl ÇALIŞKAN\n"
        "- Öğr. Gör. Mehmet DENEME – Yarı Zamanlı Öğretim Elemanları"
    )
    assert _answer_to(staff_answers, "Test Bölümü Bölüm Başkanı kim?").answer == (
        "Test Bölümü görevlileri:\n- Prof. Dr. Ayşe ÖRNEK (Bölüm Başkanı)"
    )
    assert _answer_to(
        staff_answers, "Test Bölümü Yarı Zamanlı Öğretim Elemanları kimler?"
    ).answer == ("Test Bölümü — Yarı Zamanlı Öğretim Elemanları:\n- Öğr. Gör. Mehmet DENEME")


def test_each_research_topic_lists_the_members_working_on_it(staff_answers):
    topics = [a.questions[0] for a in staff_answers if "üzerine çalışan" in a.questions[0]]
    assert topics == [
        "Algoritmalar üzerine çalışan akademisyenler kimler?",
        "Veri Madenciliği üzerine çalışan akademisyenler kimler?",
        "Yazılım Mühendisliği üzerine çalışan akademisyenler kimler?",
        "Oyun Teknolojisi üzerine çalışan akademisyenler kimler?",
    ]
    assert _answer_to(staff_answers, topics[3]).answer == (
        "Test Bölümü — araştırma konuları arasında Oyun Teknolojisi olanlar:\n"
        "- Öğr. Gör. Mehmet DENEME"
    )


def test_prepared_answers_carry_source_metadata(staff_answers, staff_source):
    for answer in staff_answers:
        assert answer.source_id == staff_source.id
        assert answer.source_title == staff_source.title
        assert answer.url == staff_source.url


def test_page_without_staff_cards_is_rejected(staff_source):
    with pytest.raises(ValueError):
        academic_staff.parse("<html><body><h1>Bakım</h1></body></html>", staff_source)
