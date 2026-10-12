"""Ayarlardan somut bileşenleri kuran bağlama noktası."""

import logging

from atilim_assistant.chat.service import ChatService
from atilim_assistant.config import Settings
from atilim_assistant.ports import ChatModel, Embedder
from atilim_assistant.providers.gemini import GeminiProvider
from atilim_assistant.providers.groq import GroqProvider
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher, PreparedAnswerStore
from atilim_assistant.retrieval.retriever import HybridRetriever
from atilim_assistant.retrieval.store import DocumentStore
from atilim_assistant.storage.mongo import (
    MongoConversationRepository,
    MongoUserRepository,
    connect,
)

logger = logging.getLogger(__name__)


def build_provider(settings: Settings) -> tuple[ChatModel, Embedder]:
    gemini = GeminiProvider(
        api_key=settings.gemini_api_key.get_secret_value(),
        llm_model=settings.llm_model,
        embed_model=settings.embed_model,
        embed_dimensions=settings.embed_dimensions,
    )
    if settings.llm_provider == "groq":
        groq_key = settings.groq_api_key.get_secret_value()
        if not groq_key:
            raise RuntimeError("LLM_PROVIDER=groq ama GROQ_API_KEY tanımlı değil.")
        chat: ChatModel = GroqProvider(api_key=groq_key, llm_model=settings.llm_model)
        logger.info("LLM: Groq (%s)", settings.llm_model)
    else:
        chat = gemini
        logger.info("LLM: Gemini (%s)", settings.llm_model)
    return chat, gemini  # (chat_model, embedder)


def build_store(settings: Settings) -> DocumentStore:
    return DocumentStore(settings.vector_store_dir, settings.collection)


def build_prepared_answer_store(settings: Settings) -> PreparedAnswerStore:
    return PreparedAnswerStore(settings.prepared_answers_path)


def build_conversation_store(
    settings: Settings,
) -> tuple[MongoUserRepository | None, MongoConversationRepository | None]:
    """MONGODB_URI tanımlı değilse geçmiş kapalıdır; asistan yine çalışır."""
    if settings.mongodb_uri is None:
        logger.warning("MONGODB_URI tanımlı değil; konuşma geçmişi ve giriş devre dışı.")
        return None, None
    db = connect(settings.mongodb_uri.get_secret_value(), settings.mongodb_db)
    return MongoUserRepository(db), MongoConversationRepository(db)


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
    chat_model, embedder = build_provider(settings)
    retriever = HybridRetriever(store, embedder, settings.retrieval_top_k)
    return ChatService(
        retriever,
        chat_model,
        PreparedAnswerMatcher(prepared_answers),
        settings.quota_cooldown_seconds,
    )
