from atilim_assistant.text import collapse_whitespace, normalize, slugify, stem, tokenize


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
