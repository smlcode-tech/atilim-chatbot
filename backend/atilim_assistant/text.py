"""Türkçe metin için arama odaklı normalleştirme."""

import re
import unicodedata

_TURKISH_I = str.maketrans("İIı", "iii")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")

# Soru kalıbı, ek ve dolgu sözcükleri (normalleştirilmiş). Bir sorunun neyi sorduğunu bunlar
# değil, geriye kalan içerik sözcükleri belirler; hazır yanıt eşleştirmesi ve anahtar kelime
# araması bu ayrıma dayanır.
FILLER_WORDS = frozenset(
    """
    acaba bana baska bir bize bu da dan de den dir dur hakkinda hangi hangileri hangisi icin ile
    in kac kim kimdir kimler kimlerdir la le lutfen merhaba mi misin misiniz mu musun musunuz
    na nasil ne nedir neler nelerdir nerede ni nin nun olan olarak selam soyle soyler su ta te
    tir tur un var ve ver verir ya ye yi
    """.split()
)


# Aynı kavramın farklı söylenişleri (normalleştirilmiş). Her grubun ilk öğesi kanonik biçimdir;
# öğeler sözcük başında eşleşir ve sondaki ekleri yutar ("maili", "mail adresine" → "eposta").
# Kanonik biçimin ilk 5 harfi başka bir sözcüğün kökü olmamalıdır (`stem`): "programciktisi"
# "program"la karışırdı. Başka sözcüklerin başı olabilecek kısa öğeler ("tel" → "televizyon")
# eklenmez.
SYNONYMS = (
    ("hoca", "ogretim uye", "ogretim eleman", "ogretmen", "akademisyen", "akademik personel",
     "akademik kadro"),
    ("eposta", "e posta", "elektronik posta", "e mail", "email", "mail"),
    ("iletisim", "ulas", "irtibat"),
    ("onkosul", "on kosul", "on sart", "onsart", "prerequisite", "prereq"),
    ("zorunlu", "mecburi", "sart mi", "zorunda"),
    ("staj", "internship"),
    ("coop", "co op", "ortak egitim", "isyeri egitim"),
    ("mufredat", "ders plan", "ogretim plan", "egitim plan", "curriculum"),
    ("yariyil", "donem", "semester"),
    ("akts", "ects"),
    ("kontenjan", "kota", "kac ogrenci al"),
    ("arastirma", "uzmanlik", "calisma alan", "ilgi alan"),
    ("pcikti", "program cikti", "ogrenme cikti", "kazanim"),
    ("kariyer", "is imkan", "is olanag", "is firsat", "is bul"),
    ("fark",),
    ("bolum baskan", "bolum sef", "bolum yonetici"),
    ("firma", "sirket"),
    ("belge", "evrak", "dokuman"),
    ("basvuru", "basvur", "muracaat"),
    ("gerek", "lazim"),
    ("universite", "okul"),
    ("yuksek lisans", "master"),
    ("doktora", "phd"),
    ("ders", "kurs"),
)
_CANONICAL = {variant: group[0] for group in SYNONYMS for variant in group}
_SYNONYM = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, _CANONICAL), key=len, reverse=True)) + r")\w*"
)


def normalize(text: str) -> str:
    """Küçük harfe çevirir, Türkçe harfleri ASCII karşılığına indirger, noktalamayı boşluk yapar."""
    folded = unicodedata.normalize("NFKD", text.translate(_TURKISH_I))
    ascii_text = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return _NON_ALNUM.sub(" ", ascii_text.lower()).strip()


def canonicalize(text: str) -> str:
    """Normalleştirir ve eş anlamlı söylenişleri kanonik biçime indirger (`SYNONYMS`).

    Sözcük eşleştirmesi anlam bilmez; "hocanın maili" ile "öğretim üyesinin e-postası" ancak
    ikisi de aynı biçime indiğinde ortak terim taşır. Soruya da kalıba/belgeye de uygulanmalıdır.
    """
    return _SYNONYM.sub(lambda match: _CANONICAL[match.group(1)], normalize(text))


def tokenize(text: str) -> list[str]:
    """Tek harfler atılır, tek haneli sayılar kalır: "3. sınıf" ile "1. sınıf" ayrı sorulardır."""
    return [token for token in normalize(text).split() if len(token) >= 2 or token.isdigit()]


def stem(token: str) -> str:
    """Çekim eklerini kabaca yok sayar: Türkçede sözcüğün ilk 5 harfi köke yakın sonuç verir."""
    return token[:5]


def slugify(text: str) -> str:
    return normalize(text).replace(" ", "-")


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()
