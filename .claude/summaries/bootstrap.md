---
source: backend/atilim_assistant/bootstrap.py
hash: 3e2861428f8d698d3afaed1a513bcebb84a12aef
updated: 2026-10-17
---

## Amaç
Ayarlardan somut bileşenleri kuran bağlama noktası. `app.py`'daki lifespan buraya çağırır.

## Public API
- `build_provider(settings) -> tuple[ChatModel, Embedder]` — LLM_PROVIDER'a göre Groq veya Gemini seçer; Embedder her zaman Gemini
- `build_store(settings) -> DocumentStore`
- `build_question_store(settings) -> DocumentStore` — `<collection>_questions`; hazır yanıt soru kalıpları, HybridRetriever'a verilir
- `build_prepared_answer_store(settings) -> PreparedAnswerStore`
- `build_conversation_store(settings) -> tuple[MongoUserRepository|None, MongoConversationRepository|None]`
- `build_chat_service(settings) -> ChatService` — indeks boşsa RuntimeError

## Dikkat
- `build_provider` bir tuple döner: `(chat_model, embedder)` — sırayı karıştırma
- `LLM_PROVIDER=groq` ama `GROQ_API_KEY` yoksa RuntimeError
- `LLM_PROVIDER!=groq` ama model adı Groq'a özgüyse RuntimeError (model adı uyuşmazlığı koruması)
- MONGODB_URI tanımlı değilse `build_conversation_store` `(None, None)` döner, exception fırlatmaz
