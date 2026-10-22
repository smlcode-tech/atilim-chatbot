"""Türkçe metin için arama odaklı normalleştirme.

Sözcük düzeyindeki her karşılaştırma (BM25, hazır yanıt eşleştirme, ders arama, ad eşleştirme)
bu dosyadaki işlevlerden geçer. Hepsi aynı kuralları kullanmalıdır: soru bir biçimde, belge
başka bir biçimde normalleştirilirse hiçbir zaman eşleşmezler.
"""

import re
import unicodedata

# "ı" Unicode ayrıştırmasıyla ASCII'ye inmez ve noktalamayla birlikte silinirdi: bu çeviri
# olmadan "ışık" → "s k" olur. "İ/I/ı" önceden "i"ye çevrilir; "ışık", "IŞIK", "isik" aynı
# sözcüğe ("isik") iner.
_TURKISH_I = str.maketrans("İIı", "iii")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")

# Soru kalıbı, ek ve dolgu sözcükleri (normalleştirilmiş). Bir sorunun neyi sorduğunu bunlar
# değil, geriye kalan içerik sözcükleri belirler; hazır yanıt eşleştirmesi ve anahtar kelime
# araması bu ayrıma dayanır.
FILLER_WORDS = frozenset(
    """
    acaba bana baska bir bize bu da dan de den dir dur hakkinda hangi hangileri hangisi icin ile
    in kac kadar kim kimdir kimler kimlerdir la le lutfen merhaba mi misin misiniz mu musun musunuz
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
    # "ulaş" fiilinin biçimleri tek tek yazılır: kök tek başına "ulaşım"ı da (taşıma) yutardı.
    ("iletisim", "ulasir", "ulasabil", "ulasma", "ulasil", "ulasac", "irtibat"),
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
    ("dayali", "yonelik", "yonelim"),
)
_CANONICAL = {variant: group[0] for group in SYNONYMS for variant in group}
# Uzun öğeler önce denenir: "ders planı" "ders" (→ ders) olarak değil, "ders plan"
# (→ mufredat) olarak eşleşmelidir.
_SYNONYM = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, _CANONICAL), key=len, reverse=True)) + r")\w*"
)


def normalize(text: str) -> str:
    """Küçük harfe çevirir, Türkçe harfleri ASCII karşılığına indirger, noktalamayı boşluk yapar.

    ASCII'ye indirmek, Türkçe klavyesi olmayan ya da harfleri atlayan kullanıcıyı da kapsar:
    "öğretim üyesi" ile "ogretim uyesi" aynı metne iner.
    """
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
    """Çekim eklerini kabaca yok sayar: Türkçede sözcüğün ilk 5 harfi köke yakın sonuç verir.

    Rakam taşıyan terimler (ders kodu, "pc3") kısaltılmaz: "cmpe113" ile "cmpe109" ayrı derslerdir.
    """
    if any(character.isdigit() for character in token):
        return token
    return token[:5]


# Ham metindeki ders kodu; harf kısmı her alfabe harfini kabul eder ("MATF", "PÇ") çünkü
# düzeltme normalleştirmeden önce, kullanıcının yazdığı metin üzerinde yapılır.
_COURSE_CODE = re.compile(r"\b([^\W\d_]{2,5}) ?(\d{3}[^\W\d_]?)\b")
# Boşluklu yazımda ("matf 276") düzeltilecek harf kısmının en kısa uzunluğu.
_MIN_SPACED_LETTERS = 4


def correct_course_codes(text: str, known: frozenset[str]) -> str:
    """Bilinmeyen ders kodunu, harf kısmı tek harf farklı olan bilinen koda çevirir:
    "MATF276" → "MATH276". Sayı kısmı aynı olmalı ve aday tek olmalıdır; birden çok koda
    benzeyen ya da hiçbirine benzemeyen koda dokunulmaz. `known` normalleştirilmiş kodlardır.

    Sayıdan boşlukla ayrılmış kısa küçük harfli sözcük kod sayılmaz: "kat 101", "oda 302" gibi
    sıradan sözcükler de tek harf uzaktaki bir koda ("KAM101") çevrilirdi.
    """

    def replace(match: re.Match) -> str:
        """Tek bir kod eşleşmesinin yerine geçecek metin; düzeltilemiyorsa yazıldığı gibi kalır."""
        letters, number = normalize(match.group(1)), normalize(match.group(2))
        if letters + number in known:
            return match.group(0)
        written = match.group(1)
        if " " in match.group(0) and len(written) < _MIN_SPACED_LETTERS and not written.isupper():
            return match.group(0)
        candidates = [
            code
            for code in known
            if code.endswith(number) and _one_edit_apart(letters, code[: -len(number)])
        ]
        return candidates[0].upper() if len(candidates) == 1 else match.group(0)

    return _COURSE_CODE.sub(replace, text)


def _one_edit_apart(a: str, b: str) -> bool:
    """Tek harf değişmiş, eklenmiş ya da eksilmiş mi."""
    if abs(len(a) - len(b)) > 1 or a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    shorter, longer = sorted((a, b), key=len)
    return any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))


def slugify(text: str) -> str:
    """URL ve kimlik için güvenli biçim ("Yaz Stajları" → "yaz-stajlari"); ayrıştırıcılar
    belge kimliklerini bununla üretir, kimlikler yeniden indekslemede değişmez."""
    return normalize(text).replace(" ", "-")


def collapse_whitespace(text: str) -> str:
    """HTML'den çıkan metindeki satır sonu ve girinti yığınlarını tek boşluğa indirir;
    gereksiz boşluklar hem indeksi hem modele giden token bütçesini şişirirdi."""
    return _WHITESPACE.sub(" ", text).strip()


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    """Satır ve sütunlu veriyi (ders saatleri, ders listeleri, kadro, müfredat) Markdown tablosu
    olarak yazar; arayüz GFM tablosu olarak gösterir, model de tabloyu olduğu gibi aktarır.

    Hücredeki "|" tabloyu böleceği için kaçırılır, satır sonları tek boşluğa iner; boş hücre
    "—" olur ki model boşluğu "bilgi yok" ile karıştırmasın.
    """

    def cell(value: object) -> str:
        text = collapse_whitespace(str(value)).replace("|", "\\|")
        return text or "—"

    lines = ["| " + " | ".join(cell(h) for h in headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)
