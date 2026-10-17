"""Takip sorularını kendi başına anlaşılır hâle getirme.

Geçmişi olan her soru modelle yeniden yazılır. Sorunun önceki turlara yaslanıp yaslanmadığını
sözcük kurallarıyla sezmek denendi ve bırakıldı: "Bu hocaların iletişim bilgileri?", "Peki
telefonu?", "Onlara nasıl ulaşırım?" aynı şeyi sayısız biçimde söyler; her kural bir kalıbı
yakalayıp bir başkasını kaçırır. Kısa bir yeniden yazma çağrısı bunların hepsini karşılar.
"""

from atilim_assistant.chat.prompts import CONTEXTUALIZE_PROMPT
from atilim_assistant.domain import Turn
from atilim_assistant.ports import ChatModel

# Modelin ürettiği yeniden yazım bundan uzunsa yanıt üretmeye kalkışmış demektir.
_MAX_REWRITE_LENGTH = 200

# Yeniden yazmak için konunun kendisi yeter; uzun yanıtların (18 kişilik kadro listesi vb.)
# tamamını göndermek dakikalık token kotasını boşuna harcar.
_MAX_TURN_CHARS = 500

_ROLE_LABELS = {"user": "Kullanıcı", "assistant": "Asistan"}


def rewrite(question: str, history: list[Turn], model: ChatModel) -> str:
    """Soruyu geçmişle birleştirip bağımsız hâle getirir; model işe yaramaz bir şey dönerse
    ham soruya düşülür."""
    transcript = "\n".join(
        f"{_ROLE_LABELS[turn.role]}: {_clip(turn.content)}" for turn in history
    )
    candidate = model.generate(
        CONTEXTUALIZE_PROMPT, f"GEÇMİŞ:\n{transcript}\n\nSON SORU: {question}"
    ).strip()
    if not candidate or "\n" in candidate or len(candidate) > _MAX_REWRITE_LENGTH:
        return question
    return candidate


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_TURN_CHARS else text[:_MAX_TURN_CHARS] + " …"
