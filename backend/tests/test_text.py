import pytest

from atilim_assistant.text import (
    canonicalize,
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
