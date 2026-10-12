"""Ayarlardan somut bileşenleri kuran bağlama noktası."""

import logging

from atilim_assistant.chat.service import ChatService
from atilim_assistant.config import Settings
from atilim_assistant.providers.gemini import GeminiProvider
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher, PreparedAnswerStore
from atilim_assistant.retrieval.retriever import HybridRetriever
from atilim_assistant.retrieval.store import DocumentStore

logger = logging.getLogger(__name__)


def build_provider(settings: Settings) -> GeminiProvider:
    return GeminiProvider(
        api_key=settings.gemini_api_key.get_secret_value(),
        llm_model=settings.llm_model,
        embed_model=settings.embed_model,
        embed_dimensions=settings.embed_dimensions,
    )


def build_store(settings: Settings) -> DocumentStore:
    return DocumentStore(settings.vector_store_dir, settings.collection)


def build_prepared_answer_store(settings: Settings) -> PreparedAnswerStore:
    return PreparedAnswerStore(settings.prepared_answers_path)


def build_chat_service(settings: Settings) -> ChatService:
    store = build_store(settings)
    if store.count() == 0:
        raise RuntimeError("İndeks boş. Önce `python -m atilim_assistant ingest` komutunu çalıştır.")
    prepared_answers = build_prepared_answer_store(settings).all()
    if not prepared_answers:
        logger.warning(
            "Hazır yanıt bulunamadı; model yanıt üretemediğinde yedek yanıt verilemeyecek. "
            "`python -m atilim_assistant ingest` komutunu yeniden çalıştır."
        )
    provider = build_provider(settings)
    retriever = HybridRetriever(store, provider, settings.retrieval_top_k)
    return ChatService(
        retriever,
        provider,
        PreparedAnswerMatcher(prepared_answers),
        settings.quota_cooldown_seconds,
    )
