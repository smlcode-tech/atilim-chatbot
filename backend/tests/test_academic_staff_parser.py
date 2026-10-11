import pytest

from atilim_assistant.ingestion.parsers import academic_staff


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
        "- Prof. Dr. Ayşe ÖRNEK (Bölüm Başkanı)\n"
        "- Arş. Gör. Işıl ÇALIŞKAN\n"
        "- Öğr. Gör. Mehmet DENEME (Yarı Zamanlı Öğretim Elemanları)"
    )


def test_documents_carry_source_metadata(staff_documents, staff_source):
    for document in staff_documents:
        assert document.source_id == staff_source.id
        assert document.source_title == staff_source.title
        assert document.url == staff_source.url


def test_page_without_staff_cards_is_rejected(staff_source):
    with pytest.raises(ValueError):
        academic_staff.parse("<html><body><h1>Bakım</h1></body></html>", staff_source)
