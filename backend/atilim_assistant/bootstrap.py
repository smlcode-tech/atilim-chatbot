"""Ayarlardan somut bileşenleri kuran bağlama noktası.

Hangi arayüzün hangi sınıfla karşılanacağı yalnızca burada bilinir (Groq, Voyage, Chroma,
MongoDB). API ve CLI bileşenleri buradan alır; testler bu dosyayı atlayıp sahte bileşenleri
doğrudan `create_app`'e verir.
"""

import logging

from atilim_assistant.chat.service import ChatService
from atilim_assistant.chat.tools import Tools
from atilim_assistant.config import Settings
from atilim_assistant.ports import ChatModel, Embedder
from atilim_assistant.providers.groq import GroqProvider
from atilim_assistant.providers.voyage import VoyageEmbedder
from atilim_assistant.retrieval.catalog import CatalogStore
from atilim_assistant.retrieval.prepared import (
    PreparedAnswerMatcher,
    PreparedAnswerStore,
)
from atilim_assistant.retrieval.retriever import HybridRetriever
from atilim_assistant.retrieval.store import DocumentStore
from atilim_assistant.storage.mongo import (
    MongoConversationRepository,
    MongoUserRepository,
    connect,
)

logger = logging.getLogger(__name__)


def build_provider(settings: Settings) -> tuple[ChatModel, Embedder]:
    """Sohbet modeli ve embedder. İkisi ayrı sağlayıcıdandır: Groq embedding sunmaz.
    Kullanılan modeller kayda yazılır ki dağıtımda hangisinin çalıştığı görülebilsin."""
    embedder: Embedder = VoyageEmbedder(
        api_key=settings.voyage_api_key.get_secret_value(),
        model=settings.embed_model,
    )
    logger.info("Embedder: Voyage AI (%s)", settings.embed_model)

    groq_key = settings.groq_api_key.get_secret_value()
    chat: ChatModel = GroqProvider(api_key=groq_key, llm_model=settings.llm_model)
    logger.info("LLM: Groq (%s)", settings.llm_model)

    return chat, embedder


def build_store(settings: Settings) -> DocumentStore:
    """Sayfa belgelerinin vektör deposu."""
    return DocumentStore(settings.vector_store_dir, settings.collection, settings.embed_model)


def build_question_store(settings: Settings) -> DocumentStore:
    """Hazır yanıtların soru kalıplarıyla aranan kopyaları; bkz. `question_documents`."""
    return DocumentStore(
        settings.vector_store_dir, f"{settings.collection}_questions", settings.embed_model
    )


def build_prepared_answer_store(settings: Settings) -> PreparedAnswerStore:
    """Hazır yanıt dosyası; ingest yazar, sohbet okur."""
    return PreparedAnswerStore(settings.prepared_answers_path)


def build_catalog_store(settings: Settings) -> CatalogStore:
    """Yapılandırılmış katalog dosyası; ingest yazar, sohbet okur."""
    return CatalogStore(settings.catalog_path)


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
    """Soru-cevap servisini tüm bileşenleriyle kurar.

    Eksik veride davranış bilinçli olarak farklıdır: belge indeksi boşsa başlamaz (asistanın
    yanıt verecek hiçbir şeyi yoktur, sessizce "bilmiyorum" demek sorunu gizlerdi); hazır
    yanıtlar ya da katalog eksikse uyarıyla başlar, çünkü asistan onlarsız da kısmen çalışır.
    """
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
    retriever = HybridRetriever(
        store,
        embedder,
        settings.retrieval_top_k,
        settings.retrieval_max_chars,
        build_question_store(settings),
    )
    catalog = build_catalog_store(settings).load()
    if not catalog.courses:
        logger.warning(
            "Katalog boş; ders ve kadro araçları sonuç vermeyecek. "
            "`python -m atilim_assistant ingest` komutunu yeniden çalıştır."
        )
    return ChatService(
        Tools(catalog, retriever),
        chat_model,
        PreparedAnswerMatcher(prepared_answers),
        settings.quota_cooldown_seconds,
    )
