from dataclasses import replace

import pytest

from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher, PreparedAnswerStore


@pytest.fixture
def matcher(staff_answers) -> PreparedAnswerMatcher:
    return PreparedAnswerMatcher(staff_answers)


@pytest.mark.parametrize(
    ("question", "answer_start"),
    [
        ("Ayşe Örnek", "**Prof. Dr. Ayşe ÖRNEK** — Test Bölümü akademik personeli"),
        ("ayşe örnek kimdir?", "**Prof. Dr. Ayşe ÖRNEK** — Test Bölümü akademik personeli"),
        ("Ayşe Örnek’in araştırma konuları neler?", "**Prof. Dr. Ayşe ÖRNEK** — araştırma konuları"),
        ("ayşe örnek hangi alanlarda çalışıyor", "**Prof. Dr. Ayşe ÖRNEK** — araştırma konuları"),
        ("ışıl çalışkanın telefonu nedir", "**Arş. Gör. Işıl ÇALIŞKAN** — telefon"),
        ("Mehmet Deneme'ye nasıl ulaşırım?", "**Öğr. Gör. Mehmet DENEME** — telefon"),
        ("Ayşe Örnek doktorasını nerede yaptı?", "**Prof. Dr. Ayşe ÖRNEK** — eğitim"),
        ("Test bölümündeki akademik personeli tanıtır mısın?", "Test Bölümü akademik kadrosu"),
        ("Bölümde kaç öğretim üyesi var?", "Test Bölümü akademik kadrosu"),
        ("Hocalar kimler?", "Test Bölümü akademik kadrosu"),
        ("Bölüm başkanı kim?", "Test Bölümü görevlileri"),
        ("yarı zamanlı hocalar kimler", "Test Bölümü — Yarı Zamanlı Öğretim Elemanları"),
        ("Veri madenciliği üzerine çalışan akademisyenler kimler?", "Test Bölümü — araştırma"),
        ("oyun teknolojisi ile ilgilenen hoca var mı", "Test Bölümü — araştırma"),
    ],
)
def test_matches_questions_despite_phrasing_suffixes_and_casing(matcher, question, answer_start):
    assert matcher.match(question).answer.startswith(answer_start)


@pytest.mark.parametrize(
    "question",
    [
        "Yemekhane menüsü nedir?",
        "Ayşe Örnek hangi dersleri veriyor?",
        "Ayşe Örnek'in odası nerede?",
        "Burs olanakları neler?",
        "Merhaba",
        "kim?",
    ],
)
def test_does_not_answer_questions_the_prepared_answers_do_not_cover(matcher, question):
    assert matcher.match(question) is None


def test_matcher_without_answers_matches_nothing():
    assert PreparedAnswerMatcher([]).match("Bölüm başkanı kim?") is None


def test_store_is_empty_before_the_first_ingest(tmp_path):
    assert PreparedAnswerStore(tmp_path / "missing.json").all() == []


def test_store_replaces_one_source_and_keeps_the_others(tmp_path, staff_answers):
    store = PreparedAnswerStore(tmp_path / "data" / "prepared_answers.json")
    other = [replace(staff_answers[0], source_id="diger-kaynak")]

    store.replace_source(staff_answers[0].source_id, staff_answers)
    store.replace_source("diger-kaynak", other)
    store.replace_source(staff_answers[0].source_id, staff_answers[:2])

    assert store.all() == other + staff_answers[:2]
