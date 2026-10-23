---
source: backend/atilim_assistant/bootstrap.py
hash: 013199efc06cf5e6d1f5c241d9c685ecd65b0e0d
updated: 2026-10-23
---

## Amaç
Ayarlardan somut bileşenleri kuran bağlama noktası; hangi arayüzü hangi sınıfın karşıladığı (Groq, Voyage, Chroma, MongoDB) yalnızca burada bilinir. `app.py` lifespan ve `cli.py` buraya çağırır; testler atlayıp sahteleri `create_app`'e verir.

## Public API
- `build_provider(settings) -> tuple[ChatModel, Embedder]` — Groq (LLM) + Voyage (embedding); kullanılan modeller kayda yazılır
- `build_store(settings) -> DocumentStore`
- `build_question_store(settings) -> DocumentStore` — `<collection>_questions`; hazır yanıt soru kalıpları
- `build_prepared_answer_store(settings) -> PreparedAnswerStore`
- `build_catalog_store(settings) -> CatalogStore` — `data/catalog.json`
- `build_conversation_store(settings) -> tuple[MongoUserRepository|None, MongoConversationRepository|None]`
- `build_chat_service(settings) -> ChatService` — `HybridRetriever(store, embedder, retrieval_top_k, question_store)` + `Tools(catalog, retriever)`

## Dikkat
- `build_provider` sırası `(chat_model, embedder)` — karıştırma
- Eksik veride davranış bilinçli olarak farklı: indeks boşsa `RuntimeError`; hazır yanıtlar ya da katalog boşsa yalnızca uyarı
- `MONGODB_URI` yoksa `build_conversation_store` `(None, None)` döner, exception fırlatmaz
- Bağlam uzunluğu sınırı artık retriever'a verilmiyor (tek sınır `chat/tools.py`'de)
