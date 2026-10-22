"""Soru-cevap akışı: model araçlarla veriyi sorgular, yanıtı kaynaklarıyla birlikte döndürür.

Model konuşma geçmişini doğrudan görür ve kullanıcının söyleyişini kendisi yorumlar; veriyi
katalog ve belge araçlarıyla (`chat/tools.py`) alır. Model yanıt üretemezse (kota, ağ, zaman
aşımı) soru hazır yanıtlarla karşılanır.
"""

import logging
import time

from atilim_assistant.chat.prompts import NO_ANSWER, SUGGESTIONS_INTRO, system_prompt
from atilim_assistant.chat.tools import DEFINITIONS, Tools
from atilim_assistant.domain import Answer, Citation, Completion, PreparedAnswer, Turn
from atilim_assistant.ports import ChatModel
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher

logger = logging.getLogger(__name__)

# Model bir kez başarısız olduktan sonra bu süre boyunca, hazır yanıtı olan sorularda model
# hiç denenmez; yoksa kesinti sürerken her kullanıcı yeniden denemelerin bitmesini beklerdi.
_TRANSIENT_COOLDOWN_SECONDS = 60

# Günlük kota bittiğinde yeniden denemek bir sonraki güne kadar boşunadır; geçici hata
# bekleyişiyle aynı süreyi kullanmak dakikada bir çağrı harcar. Groq'un dakikalık token sınırı
# (TPM) da 429 döner ama dakika içinde açılır: yalnızca günlük sınırlar ("tokens per day (TPD)",
# "requests per day (RPD)") uzun bekleyişe yol açar, diğer 429'lar geçici hatadır.
_DAILY_QUOTA_MARKERS = ("per day", "(TPD)", "(RPD)")

# Araç çağrısı turu sınırı; son turda araç verilmez, model eldekiyle yanıtlamak zorunda kalır.
# Her tur bir model çağrısıdır ve dakikalık token kotasından yer.
_MAX_TOOL_ROUNDS = 4

# Geçmişteki uzun yanıtların (18 kişilik kadro listesi vb.) tamamı gerekmez; konu yeter.
_MAX_TURN_CHARS = 1500

# Yanıtlanamayan soruda sunulan yakın soru sayısı.
_SUGGESTION_COUNT = 5

# Modelin yanıtın başına koyabildiği Markdown işaretleri ve boşluk.
_MARKUP = " \t\n*_>#"


class ChatService:
    """Bir soruyu yanıta çeviren tek giriş noktası; API katmanı yalnızca bunu çağırır.

    Bileşenler (`ChatModel`, araçlar, hazır yanıtlar) dışarıdan verilir: üretimde
    `bootstrap.build_chat_service` bağlar, testler sahte model verir. Model durumu (soğuma
    saatleri) nesnede tutulur ve tüm kullanıcılar arasında paylaşılır: kesinti kullanıcıya
    değil, Groq'a özgüdür.
    """

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
        # Günlük kota bitince modelin dinlendirileceği süre; ayarlanabilir, testler kısaltır.
        self._quota_cooldown_seconds = quota_cooldown_seconds
        # Bu saate kadar hazır yanıtı olan sorular modele gönderilmez (her hatada ilerler).
        self._model_retry_at = 0.0
        # Bu saate kadar hiçbir soru modele gönderilmez (yalnızca günlük kota hatasında ilerler).
        self._quota_reset_at = 0.0

    def answer(self, question: str, history: list[Turn] | None = None) -> Answer:
        """Soruyu yanıtlar; sıra: kod düzeltme → birebir hazır yanıt → model → hazır yanıt yedeği.

        `history`: önceki turlar; takip sorularını ("bu hocalar") model bunlardan çözer.

        Model de hazır yanıtlar da soruyu karşılayamazsa modelin hatasını yükseltir. Hata
        yutulmaz: API katmanı bunu görüp soruyu kullanıcının günlük sınırından geri düşer ve
        boş ya da uydurma bir yanıt yerine hata döndürür.
        """
        # Yanlış yazılmış ders kodu en başta düzeltilir; model de hazır yanıtlar da doğru
        # kodu görür.
        question = self._tools.correct(question)
        # Önerilen bir soru seçildiğinde soru bir hazır yanıt kalıbının kendisidir; yanıtı
        # kesindir ve modele sormak hem kota harcar hem de modelin onu bulamaması olasıdır.
        exact = self._prepared_answers.exact(question)
        if exact:
            return _prepared_answer(exact)
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
            answer = self._converse(question, history or [])
        except Exception as error:
            self._note_failure(error)
            prepared = self._prepared_answers.match(question)
            if prepared:
                logger.warning("Model yanıt veremedi, hazır yanıt verildi: %s", error)
                return _prepared_answer(prepared)
            raise
        if _says_no_answer(answer.text):
            return self._with_suggestions(question, answer)
        return answer

    def _with_suggestions(self, question: str, answer: Answer) -> Answer:
        """"Bilmiyorum" yerine soruya en yakın, yanıtı olan soruları seçenek olarak sunar;
        kullanıcı belki de bunlardan birini soruyordu. Yakın soru bulunamazsa model yanıtı kalır."""
        try:
            suggestions = self._tools.suggest(question, _SUGGESTION_COUNT)
        except Exception as error:
            logger.warning("Yakın sorular getirilemedi: %s", error)
            return answer
        if not suggestions:
            return answer
        return Answer(text=SUGGESTIONS_INTRO, citations=[], suggestions=suggestions)

    def _converse(self, question: str, history: list[Turn]) -> Answer:
        """Araç çağrılı model döngüsü: model araç istedikçe çalıştırılır, sonuçları mesaj olarak
        geri verilir; model araçsız yanıt verince döngü biter.

        Kaynaklar araç sonuçlarından toplanır, modelin metninden değil; model kaynak
        uyduramaz. Aynı sayfa birden çok araçtan gelirse bir kez gösterilir.
        """
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
                sources = [] if _says_no_answer(text) else list(citations.values())
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
        """Model hatasından sonra modelin ne kadar dinlendirileceğini belirler.

        Hata türü mesajdan anlaşılır çünkü Groq günlük ve dakikalık sınırların ikisinde de aynı
        hata sınıfını (429) döndürür; ayrım yalnızca metindedir (bkz. `_DAILY_QUOTA_MARKERS`).
        """
        quota = any(marker in str(error) for marker in _DAILY_QUOTA_MARKERS)
        wait = self._quota_cooldown_seconds if quota else _TRANSIENT_COOLDOWN_SECONDS
        self._model_retry_at = time.monotonic() + wait
        if quota:
            self._quota_reset_at = self._model_retry_at


def _assistant_message(completion: Completion) -> dict:
    """Modelin araç isteğini OpenAI mesaj biçimine geri çevirir.

    Araç sonuçları (`role: tool`) `tool_call_id` ile bu mesaja bağlanır; istek geçmişe
    eklenmezse API sonuçları sahipsiz sayıp isteği reddeder.
    """
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


def _says_no_answer(text: str) -> bool:
    """Model `NO_ANSWER` cümlesiyle mi başladı; başına koyduğu biçim işaretleri ("**", "> ")
    yok sayılır, yoksa yanıt kaynaklı gösterilir ve yerine yakın sorular önerilmezdi."""
    return text.lstrip(_MARKUP).startswith(NO_ANSWER)


def _clip(text: str) -> str:
    """Geçmişteki bir turu kısaltır (bkz. `_MAX_TURN_CHARS`). Sonuna "…" eklenir; sistem
    talimatı da modele kısaltılmış listelere güvenmemesini ve aracı yeniden çağırmasını söyler."""
    return text if len(text) <= _MAX_TURN_CHARS else text[:_MAX_TURN_CHARS] + " …"


def _prepared_answer(prepared: PreparedAnswer) -> Answer:
    """Hazır yanıtı `Answer`'a çevirir. `prepared=True` API yanıtına ve arayüzün mesaj durumuna
    (`isPrepared`) taşınır; modelsiz verilen yanıtlar böylece ayırt edilebilir."""
    citation = Citation(title=prepared.source_title, url=prepared.url)
    return Answer(text=prepared.answer, citations=[citation], prepared=True)
