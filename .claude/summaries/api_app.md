---
source: backend/atilim_assistant/api/app.py
hash: 3962a97091597dba28a6b7e3fce9622d730e1290
updated: 2026-10-19
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

## Misafir ve öneriler (2026-10-19)
- Misafir: `chat_user` None döner; misafir `body.history` ile geçmiş gönderir, `_guest_key` (X-Forwarded-For son öğesinin SHA-256 özeti) ile `count_guest_question` üzerinden günlük `guest_daily_question_limit` uygulanır; `/api/health` `guest_question_limit` döndürür
