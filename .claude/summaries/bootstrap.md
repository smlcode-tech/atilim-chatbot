---
source: backend/atilim_assistant/bootstrap.py
hash: 45262763078a7f1b117beca27e99900731b2416f
updated: 2026-10-18
---

## Amaç
Ayarlardan somut bileşenleri kuran bağlama noktası. `app.py`'daki lifespan ve `cli.py` buraya çağırır.

## Public API
- `build_provider(settings) -> tuple[ChatModel, Embedder]` — Groq (LLM) + Voyage (embedding)
- `build_store(settings) -> DocumentStore`
- `build_question_store(settings) -> DocumentStore` — `<collection>_questions`; hazır yanıt soru kalıpları
- `build_prepared_answer_store(settings) -> PreparedAnswerStore`
- `build_catalog_store(settings) -> CatalogStore` — `data/catalog.json`
- `build_conversation_store(settings) -> tuple[MongoUserRepository|None, MongoConversationRepository|None]`
- `build_chat_service(settings) -> ChatService` — `Tools(catalog, retriever)` kurar; indeks boşsa RuntimeError, katalog boşsa uyarı

## Dikkat
- `build_provider` bir tuple döner: `(chat_model, embedder)` — sırayı karıştırma
- MONGODB_URI tanımlı değilse `build_conversation_store` `(None, None)` döner, exception fırlatmaz
