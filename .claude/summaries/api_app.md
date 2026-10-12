---
source: backend/atilim_assistant/api/app.py
hash: 1181a643366da79f5d82d4a1aad7cddd7d67c1fa
updated: 2026-10-12
---

## Amaç
FastAPI uygulama fabrikası. Tüm HTTP rotaları burada tanımlı; bileşenler `app.state`'e bağlanır.

## Public API
- `create_app(chat_service?, users?, settings?, conversations?) -> FastAPI` — testler sahte bileşen enjekte eder
- `GET /api/health` → `HealthResponse`
- `POST /api/auth/google` body: `{id_token}` → `SignInResponse`
- `GET /api/auth/me` → `UserResponse`
- `POST /api/chat` body: `{question, conversation_id?}` → `ChatResponse`
- `GET /api/conversations` → `list[ConversationSummaryResponse]`
- `GET /api/conversations/{id}` → `ConversationResponse`
- `DELETE /api/conversations/{id}` → 204

## Önemli Kısıtlamalar
- MongoDB kapalıysa lifespan hata fırlatmaz; asistan geçmişsiz devam eder
- Günlük soru limiti 429 döner; sayaç güncellenemezse soru yine geçer
- `history_turns` ayarı kadar tur `_resume()` ile çekilir
- Konuşma başlığı sorunun ilk 60 karakterinden alınır
