import pytest

from atilim_assistant.text import (
    canonicalize,
    correct_course_codes,
    collapse_whitespace,
    normalize,
    slugify,
    stem,
    tokenize,
)


def test_normalize_folds_turkish_letters_and_punctuation():
    assert normalize("Işıl ÇALIŞKAN'ın Yapay Zekâ çalışması") == "isil caliskan in yapay zeka calismasi"


def test_tokenize_drops_single_letter_tokens():
    assert tokenize("Yazıcı'nın e-Devlet projesi") == ["yazici", "nin", "devlet", "projesi"]


def test_stem_ignores_inflectional_suffixes():
    assert stem("yazicinin") == stem("yazici")
    assert stem("calisiyor") == stem("calisan")
    assert stem("ali") == "ali"
    # Ders kodları kısaltılırsa "CMPE113" sorusu "CMPE109"un yanıtını alır.
    assert stem("cmpe113") != stem("cmpe109")


def test_slugify():
    assert slugify("Prof. Dr. Ayşe ÖRNEK") == "prof-dr-ayse-ornek"


def test_collapse_whitespace():
    assert collapse_whitespace("  Algoritmalar,\n\n   Veri  ") == "Algoritmalar, Veri"


@pytest.mark.parametrize(
    ("variants", "canonical"),
    [
        (["mail adresi", "e-postası", "E-Mail", "elektronik posta"], "eposta adresi"),
        (["öğretim üyeleri", "akademisyenler", "hocası", "öğretmen"], "hoca"),
        (["ön şartı", "önkoşulu", "ön koşul", "prerequisite"], "onkosul"),
        (["mecburi", "zorunlu mu", "şart mı"], "zorunlu"),
    ],
)
def test_canonicalize_folds_synonyms_and_their_suffixes(variants, canonical):
    for variant in variants:
        assert canonicalize(variant).startswith(canonical.split()[0])
    assert canonicalize("Hocanın mail adresi") == "hoca eposta adresi"


def test_canonicalize_leaves_unrelated_words_alone():
    # Sözcük ortasında ya da başka bir sözcüğün başında geçen öğe eşleşmez.
    assert canonicalize("Gmail telefon başvurusu") == "gmail telefon basvuru"
    assert canonicalize("Ali Yazıcı") == "ali yazici"
    # "ulaşım" (taşıma) "ulaşmak"la (iletişim) aynı kökten gelir ama başka bir şey sorar.
    assert canonicalize("Kampüse ulaşım") == "kampuse ulasim"


@pytest.mark.parametrize("phrase", ["nasıl ulaşırım", "ulaşabilir miyim", "ulaşmak", "ulaşılır"])
def test_reaching_someone_means_contact(phrase):
    assert "iletisim" in canonicalize(phrase)


_CODES = frozenset({"math276", "math275", "se212", "se221", "cmpe113", "kam101", "ode276"})


@pytest.mark.parametrize(
    ("question", "corrected"),
    [
        ("MATF276", "MATH276"),
        ("matf 276 dersini kim veriyor", "MATH276 dersini kim veriyor"),
        ("MAT276 hakkında bilgi", "MATH276 hakkında bilgi"),
        ("CMPEE113", "CMPE113"),
        # Bilinen kodlar, sayısı tutmayan ya da hiçbir koda benzemeyen kodlar değişmez.
        ("MATH276", "MATH276"),
        ("SE 212", "SE 212"),
        ("MATF999", "MATF999"),
        ("PHYS276", "PHYS276"),
        ("Bölümün 2024 kontenjanı", "Bölümün 2024 kontenjanı"),
        # Sayıdan önce gelen sıradan kısa sözcük kod değildir.
        ("kat 101 nerede", "kat 101 nerede"),
        ("oda 276", "oda 276"),
        ("MAT 276", "MATH276"),
    ],
)
def test_correct_course_codes_fixes_one_letter_typos(question, corrected):
    assert correct_course_codes(question, _CODES) == corrected


def test_correct_course_codes_leaves_ambiguous_codes_alone():
    # "SF221" hem "SE221"e hem "SA221"e tek harf uzak.
    assert correct_course_codes("SF221", _CODES | {"sa221"}) == "SF221"
