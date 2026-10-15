"""Takip sorularını kendi başına anlaşılır hâle getirme.

Modeli her soruda ikinci kez çağırmak ücretsiz katmanın günlük kotasını ikiye böler. Bu yüzden
yeniden yazma, yalnızca sorunun önceki turlara yaslandığı durumlarda yapılır; kararı veren kapı
`needs_context`.
"""

from atilim_assistant.chat.prompts import CONTEXTUALIZE_PROMPT
from atilim_assistant.domain import Turn
from atilim_assistant.ports import ChatModel
from atilim_assistant.text import FILLER_WORDS, stem, tokenize

# Bu sayıdan fazla içerik sözcüğü taşıyan soru, kendi konusunu kurmuş sayılır: "Blok zinciri ile
# ilgilenen öğretim üyeleri kimler?" özel ad içermez ama önceki turlara ihtiyaç duymaz.
_MAX_STANDALONE_TERMS = 3

# Modelin ürettiği yeniden yazım bundan uzunsa yanıt üretmeye kalkışmış demektir.
_MAX_REWRITE_LENGTH = 200

# Yalnızca önceki tura işaret edebilen çekimli zamirler ve takip belirteçleri. Bunlar bir soruda
# geçiyorsa soru uzunluğundan bağımsız olarak geçmişe yaslanıyordur.
_PRONOUNS = frozenset(
    """
    onu onun ona ondan onlari onlarin bunu bunun buna bundan bunlari sunu sunun
    orada oraya oradaki ayni oyle boyle digeri digerleri oburu detay detayli ozetle kisalt
    """.split()
)

# Hem işaret zamiri hem sıradan belirteç olabilen sözcükler: "bu bölümde kaç kişi var?" geçmişe
# yaslanır ama "bu yıl kaç öğrenci mezun oldu?" yaslanmaz. Yalnızca kısa sorularda sayılırlar.
_WEAK_DETERMINERS = frozenset("bu su onlar bunlar sunlar daha devam tekrar ornek".split())

# Soruyu bir öncekine bağlayan açılışlar.
DISCOURSE_OPENERS = frozenset("peki ya yani ayrica hani sonra".split())

_ROLE_LABELS = {"user": "Kullanıcı", "assistant": "Asistan"}


def needs_context(question: str, history: list[Turn]) -> bool:
    """Soru önceki turlar olmadan anlaşılmıyorsa True.

    Yanlış pozitifin bedeli fazladan bir model çağrısı, yanlış negatifin bedeli yanlış yanıttır;
    bu yüzden kararsız kalan sorular yeniden yazmaya gönderilir.
    """
    if not history:
        return False

    tokens = tokenize(question)
    if not tokens:
        return False

    if tokens[0] in DISCOURSE_OPENERS or _PRONOUNS & set(tokens):
        return True

    content = {stem(token) for token in tokens if token not in FILLER_WORDS}
    if len(content) > _MAX_STANDALONE_TERMS:
        return False

    if _WEAK_DETERMINERS & set(tokens):
        return True

    return not _names_an_entity(question)


def rewrite(question: str, history: list[Turn], model: ChatModel) -> str:
    """Soruyu geçmişle birleştirip bağımsız hâle getirir; model işe yaramaz bir şey dönerse
    ham soruya düşülür."""
    transcript = "\n".join(f"{_ROLE_LABELS[turn.role]}: {turn.content}" for turn in history)
    candidate = model.generate(
        CONTEXTUALIZE_PROMPT, f"GEÇMİŞ:\n{transcript}\n\nSON SORU: {question}"
    ).strip()
    if not candidate or "\n" in candidate or len(candidate) > _MAX_REWRITE_LENGTH:
        return question
    return candidate


def _names_an_entity(question: str) -> bool:
    """İlk sözcükten sonra büyük harfle başlayan bir sözcük özel ad sayılır: soru kendi öznesini
    getirmiştir. Yalnızca büyük harften oluşan kısaltmalar ("AKTS", "GPA") sayılmaz; bunlar
    nitelik bildirir, özne değildir. Ders kodu gibi rakam içerenler ("SE322") yine özne sayılır."""
    return any(_is_name(word.strip("?!.,;:'\"’")) for word in question.split()[1:])


def _is_name(word: str) -> bool:
    if not word[:1].isupper():
        return False
    letters = "".join(ch for ch in word.split("'")[0].split("’")[0] if ch.isalpha())
    is_acronym = letters.isupper() and not any(ch.isdigit() for ch in word)
    return not is_acronym
