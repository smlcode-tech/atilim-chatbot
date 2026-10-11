"""Soru-cevap akışı: ilgili belgeleri getir, modele sor, kaynaklarıyla birlikte döndür.

Model yanıt üretemezse (kota, ağ, zaman aşımı) soru hazır yanıtlarla karşılanır.
"""

import logging
import time

from atilim_assistant.chat.prompts import SYSTEM_PROMPT, build_prompt
from atilim_assistant.domain import Answer, Citation, Document, PreparedAnswer
from atilim_assistant.ports import ChatModel
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher
from atilim_assistant.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Model bir kez başarısız olduktan sonra bu süre boyunca, hazır yanıtı olan sorularda model
# hiç denenmez; yoksa kesinti sürerken her kullanıcı yeniden denemelerin bitmesini beklerdi.
_MODEL_COOLDOWN_SECONDS = 60


class ChatService:
    def __init__(
        self, retriever: HybridRetriever, model: ChatModel, prepared_answers: PreparedAnswerMatcher
    ) -> None:
        self._retriever = retriever
        self._model = model
        self._prepared_answers = prepared_answers
        self._model_retry_at = 0.0

    def answer(self, question: str) -> Answer:
        """Model de hazır yanıtlar da soruyu karşılayamazsa modelin hatasını yükseltir."""
        prepared = self._prepared_answers.match(question)
        if prepared and time.monotonic() < self._model_retry_at:
            return _prepared_answer(prepared)
        try:
            return self._generate(question)
        except Exception as error:
            self._model_retry_at = time.monotonic() + _MODEL_COOLDOWN_SECONDS
            if prepared is None:
                raise
            logger.warning("Model yanıt üretemedi, hazır yanıt veriliyor: %s", error)
            return _prepared_answer(prepared)

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
