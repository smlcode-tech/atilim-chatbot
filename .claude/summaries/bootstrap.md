---
source: backend/atilim_assistant/bootstrap.py
hash: e93d0ef7f5c7ac34bc37f7d93d9dbbb9f7d7ec6d
updated: 2026-10-12
---

## Amaç
Ayarlardan somut bileşenleri kuran bağlama noktası. `app.py`'daki lifespan buraya çağırır.

## Public API
- `build_provider(settings) -> tuple[ChatModel, Embedder]` — LLM_PROVIDER'a göre Groq veya Gemini seçer; Embedder her zaman Gemini
- `build_store(settings) -> DocumentStore`
- `build_prepared_answer_store(settings) -> PreparedAnswerStore`
- `build_conversation_store(settings) -> tuple[MongoUserRepository|None, MongoConversationRepository|None]`
- `build_chat_service(settings) -> ChatService` — indeks boşsa RuntimeError

## Dikkat
- `build_provider` bir tuple döner: `(chat_model, embedder)` — sırayı karıştırma
- `LLM_PROVIDER=groq` ama `GROQ_API_KEY` yoksa RuntimeError
- `LLM_PROVIDER!=groq` ama model adı Groq'a özgüyse RuntimeError (model adı uyuşmazlığı koruması)
- MONGODB_URI tanımlı değilse `build_conversation_store` `(None, None)` döner, exception fırlatmaz
