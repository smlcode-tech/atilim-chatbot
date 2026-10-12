"""Soru-cevap akışı: ilgili belgeleri getir, modele sor, kaynaklarıyla birlikte döndür.

Model yanıt üretemezse (kota, ağ, zaman aşımı) soru hazır yanıtlarla karşılanır.
"""

import logging
import time

from atilim_assistant.chat.contextualize import needs_context, rewrite
from atilim_assistant.chat.prompts import SYSTEM_PROMPT, build_prompt
from atilim_assistant.domain import Answer, Citation, Document, PreparedAnswer, Turn
from atilim_assistant.ports import ChatModel
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher
from atilim_assistant.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Model bir kez başarısız olduktan sonra bu süre boyunca, hazır yanıtı olan sorularda model
# hiç denenmez; yoksa kesinti sürerken her kullanıcı yeniden denemelerin bitmesini beklerdi.
_TRANSIENT_COOLDOWN_SECONDS = 60

# Kota bittiğinde yeniden denemek bir sonraki güne kadar boşunadır; geçici hata bekleyişiyle
# aynı süreyi kullanmak dakikada bir çağrı harcar.
_QUOTA_MARKERS = ("RESOURCE_EXHAUSTED", "429")


class ChatService:
    def __init__(
        self,
        retriever: HybridRetriever,
        model: ChatModel,
        prepared_answers: PreparedAnswerMatcher,
        quota_cooldown_seconds: int = 3600,
    ) -> None:
        self._retriever = retriever
        self._model = model
        self._prepared_answers = prepared_answers
        self._quota_cooldown_seconds = quota_cooldown_seconds
        self._model_retry_at = 0.0

    def answer(self, question: str, history: list[Turn] | None = None) -> Answer:
        """Model de hazır yanıtlar da soruyu karşılayamazsa modelin hatasını yükseltir."""
        search_question = self._standalone(question, history or [])
        prepared = self._prepared_answers.match(search_question)
        if prepared and self._cooling():
            return _prepared_answer(prepared)
        try:
            return self._generate(search_question)
        except Exception as error:
            self._note_failure(error)
            if prepared is None:
                raise
            logger.warning("Model yanıt üretemedi, hazır yanıt veriliyor: %s", error)
            return _prepared_answer(prepared)

    def _standalone(self, question: str, history: list[Turn]) -> str:
        """Takip sorusunu bağımsız hâle getirir; gerekmiyorsa soruyu aynen döndürür.

        Ham soru bir hazır yanıta eşleşiyor diye yeniden yazmayı atlamak yanlış olurdu:
        "Araştırma konuları neler?" bir yanıtı tutturur ama bu, geçmişte konuşulan kişinin
        yanıtı olmayabilir.
        """
        if self._cooling() or not needs_context(question, history):
            return question
        try:
            return rewrite(question, history, self._model)
        except Exception as error:
            self._note_failure(error)
            logger.warning("Soru bağlamlandırılamadı, ham soru kullanılıyor: %s", error)
            return question

    def _cooling(self) -> bool:
        return time.monotonic() < self._model_retry_at

    def _note_failure(self, error: Exception) -> None:
        quota = any(marker in str(error) for marker in _QUOTA_MARKERS)
        wait = self._quota_cooldown_seconds if quota else _TRANSIENT_COOLDOWN_SECONDS
        self._model_retry_at = time.monotonic() + wait

    def _generate(self, question: str) -> Answer:
        documents = self._retriever.retrieve(question)
        text = self._model.generate(SYSTEM_PROMPT, build_prompt(question, documents)).strip()
        if not text:
            raise RuntimeError("Model boş yanıt döndürdü.")
        return Answer(text=text, citations=_citations(documents))


def _prepared_answer(prepared: PreparedAnswer) -> Answer:
    citation = Citation(title=prepared.source_title, url=prepared.url)
    return Answer(text=prepared.answer, citations=[citation], prepared=True)


def _citations(documents: list[Document]) -> list[Citation]:
    """Getirilen belgelerin geldiği sayfalar; aynı sayfa bir kez listelenir."""
    pages = {document.url: document.source_title for document in documents}
    return [Citation(title=title, url=url) for url, title in pages.items()]
