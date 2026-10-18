"""Soru-cevap akışı: model araçlarla veriyi sorgular, yanıtı kaynaklarıyla birlikte döndürür.

Model konuşma geçmişini doğrudan görür ve kullanıcının söyleyişini kendisi yorumlar; veriyi
katalog ve belge araçlarıyla (`chat/tools.py`) alır. Model yanıt üretemezse (kota, ağ, zaman
aşımı) soru hazır yanıtlarla karşılanır.
"""

import logging
import time

from atilim_assistant.chat.prompts import NO_ANSWER, system_prompt
from atilim_assistant.chat.tools import DEFINITIONS, Tools
from atilim_assistant.domain import Answer, Citation, Completion, PreparedAnswer, Turn
from atilim_assistant.ports import ChatModel
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher

logger = logging.getLogger(__name__)

# Model bir kez başarısız olduktan sonra bu süre boyunca, hazır yanıtı olan sorularda model
# hiç denenmez; yoksa kesinti sürerken her kullanıcı yeniden denemelerin bitmesini beklerdi.
_TRANSIENT_COOLDOWN_SECONDS = 60

# Kota bittiğinde yeniden denemek bir sonraki güne kadar boşunadır; geçici hata bekleyişiyle
# aynı süreyi kullanmak dakikada bir çağrı harcar.
_QUOTA_MARKERS = ("RESOURCE_EXHAUSTED", "429")

# Araç çağrısı turu sınırı; son turda araç verilmez, model eldekiyle yanıtlamak zorunda kalır.
# Her tur bir model çağrısıdır ve dakikalık token kotasından yer.
_MAX_TOOL_ROUNDS = 4

# Geçmişteki uzun yanıtların (18 kişilik kadro listesi vb.) tamamı gerekmez; konu yeter.
_MAX_TURN_CHARS = 1500


class ChatService:
    def __init__(
        self,
        tools: Tools,
        model: ChatModel,
        prepared_answers: PreparedAnswerMatcher,
        quota_cooldown_seconds: int = 3600,
    ) -> None:
        self._tools = tools
        self._model = model
        self._prepared_answers = prepared_answers
        self._quota_cooldown_seconds = quota_cooldown_seconds
        self._model_retry_at = 0.0
        self._quota_reset_at = 0.0

    def answer(self, question: str, history: list[Turn] | None = None) -> Answer:
        """Model de hazır yanıtlar da soruyu karşılayamazsa modelin hatasını yükseltir."""
        # Yanlış yazılmış ders kodu en başta düzeltilir; model de hazır yanıtlar da doğru
        # kodu görür.
        question = self._tools.correct(question)
        if time.monotonic() < self._model_retry_at:
            # Kesinti sürerken hazır yanıtı olan soru modeli beklemez. Geçmiş modelsiz
            # yorumlanamadığı için ham soru eşleştirilir.
            prepared = self._prepared_answers.match(question)
            if prepared:
                return _prepared_answer(prepared)
            # Kota bitmişken her soruyu modele göndermek yalnızca reddedilen istek biriktirir.
            # Geçici hatalarda ise model denenir: kesinti tek bir isteğe özgü olabilir.
            if time.monotonic() < self._quota_reset_at:
                raise RuntimeError("Model kotası doldu; bekleme süresi bitmedi.")
        try:
            return self._converse(question, history or [])
        except Exception as error:
            self._note_failure(error)
            prepared = self._prepared_answers.match(question)
            if prepared:
                logger.warning("Model yanıt veremedi, hazır yanıt verildi: %s", error)
                return _prepared_answer(prepared)
            raise

    def _converse(self, question: str, history: list[Turn]) -> Answer:
        messages: list[dict] = [{"role": "system", "content": system_prompt(self._tools.term)}]
        messages += [{"role": turn.role, "content": _clip(turn.content)} for turn in history]
        messages.append({"role": "user", "content": question})

        citations: dict[str, Citation] = {}
        for round_number in range(_MAX_TOOL_ROUNDS + 1):
            tools = DEFINITIONS if round_number < _MAX_TOOL_ROUNDS else []
            completion = self._model.complete(messages, tools)
            if not completion.tool_calls:
                text = completion.content.strip()
                if not text:
                    raise RuntimeError("Model boş yanıt döndürdü.")
                # Model veriyi yetersiz bulduysa sorgulanan sayfalar yanıtın kaynağı değildir.
                sources = [] if text.startswith(NO_ANSWER) else list(citations.values())
                return Answer(text=text, citations=sources)

            messages.append(_assistant_message(completion))
            for call in completion.tool_calls:
                result = self._tools.run(call.name, call.arguments)
                logger.info("Araç %s(%s): %d karakter", call.name, call.arguments, len(result.text))
                for citation in result.citations:
                    citations.setdefault(citation.url, citation)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result.text})
        raise RuntimeError("Model araç turu sınırında yanıt üretmedi.")

    def _note_failure(self, error: Exception) -> None:
        quota = any(marker in str(error) for marker in _QUOTA_MARKERS)
        wait = self._quota_cooldown_seconds if quota else _TRANSIENT_COOLDOWN_SECONDS
        self._model_retry_at = time.monotonic() + wait
        if quota:
            self._quota_reset_at = self._model_retry_at


def _assistant_message(completion: Completion) -> dict:
    return {
        "role": "assistant",
        "content": completion.content,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in completion.tool_calls
        ],
    }


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_TURN_CHARS else text[:_MAX_TURN_CHARS] + " …"


def _prepared_answer(prepared: PreparedAnswer) -> Answer:
    citation = Citation(title=prepared.source_title, url=prepared.url)
    return Answer(text=prepared.answer, citations=[citation], prepared=True)
