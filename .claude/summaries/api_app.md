---
source: backend/atilim_assistant/api/app.py
hash: d84d8969d915b118af76f0f63ac0f9bdc9eb4da5
updated: 2026-11-03
---

## Amaç
FastAPI uygulama fabrikası. Tüm HTTP rotaları burada; bileşenler lifespan'de bir kez kurulup `app.state`'e bağlanır. Yalnızca HTTP'yi bilir (kimlik, günlük sınır, geçmiş, hata kodları); yanıtlama `ChatService`'te.

## Public API
- `create_app(chat_service?, users?, settings?, conversations?) -> FastAPI` — testler sahte bileşen enjekte eder; modül düzeyinde `app` yok (`--factory`)
- `GET /api/health` → `HealthResponse(status, auth_required, guest_question_limit)` — dış servise dokunmaz
- `POST /api/auth/google` body `{id_token}` → `SignInResponse`; 401 geçersiz jeton, 503 giriş altyapısı yok
- `GET /api/auth/me` → `UserResponse`
- `POST /api/chat` body `{question, conversation_id?, history?}` → `ChatResponse` (`remaining` dahil); sıra: günlük sınır → geçmiş → yanıt → kayıt
- `GET /api/quota` → `QuotaResponse(limit, remaining)` — sayacı değiştirmeden okur
- `GET /api/conversations` → `list[ConversationSummaryResponse]`
- `GET /api/conversations/{id}` → `ConversationResponse` (başkasının konuşması da 404)
- `DELETE /api/conversations/{id}` → 204

## Önemli Kısıtlamalar
- Mongo'ya bağlanılamazsa lifespan hata fırlatmaz; geçmişsiz ve misafir olarak devam eder
- Giriş yalnızca `google_client_id` + kullanıcı deposu varken ve `JWT_SECRET` ≥ 32 bayt ise açık (`MIN_JWT_SECRET_BYTES`)
- `RequestValidationError` → Türkçe tek `detail` ile 422
- Günlük sınır yanıttan **önce** düşülür (eşzamanlı istekler aşamasın); aşılırsa 429. Yanıt üretilemezse sayaç `uncount_*` ile geri alınır ve 502 (`UNAVAILABLE_DETAIL`)
- Sayaç tutulamıyorsa (depo yok ya da hata) süreç içi `_MemoryQuota` yedek sayacı kullanılır; sınır kalkmaz, `/api/quota` da onu okur. Yeniden başlatmada sıfırlanır
- `/docs`, `/redoc`, `/openapi.json` kapalı
- `_daily_limit`: girişliye `daily_question_limit`, misafire `guest_daily_question_limit`; soru ucu ve `/api/quota` aynı kuralı kullanır
- Geçmiş okunamazsa soru geçmişsiz yanıtlanır ve kayıt da denenmez; kayıt başarısızsa yanıt yine verilir
- Konuşma uçlarında depo yok/ulaşılamıyorsa 503 (`_from_history`, `HISTORY_UNAVAILABLE_DETAIL`)
- `history_turns` kadar son tur kullanılır (`_last`; 0 → boş); başlık sorunun ilk 60 karakteri (`_title_from`), model çağrılmaz
- Kaydedilen kullanıcı turu ham sorudur (ders kodu düzeltmesi geçmişe yazılmaz)

## Misafir ve IP
- Misafir: `chat_user` None; geçmiş `body.history`'den gelir, konuşma kaydedilmez
- `_guest_key`: istemci IP'sinin SHA-256 özeti (adres saklanmaz); `_subscriber` IPv6'yı /64 önekine indirir (blok içinde adres değiştirerek sınır aşılmasın)
- `_client_ip`: `X-Proxy-Secret` `proxy_secret` ile eşleşirse (`hmac.compare_digest`) `X-Vercel-Forwarded-For` / `X-Real-IP` / `X-Forwarded-For` ilk öğesi; eşleşmezse `X-Forwarded-For`'un **son** öğesi (Render ekler), o da yoksa `request.client.host`
