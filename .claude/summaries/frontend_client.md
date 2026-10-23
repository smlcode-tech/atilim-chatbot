---
source: frontend/src/api/client.ts
hash: ac2853e20c8c17890c8de4d068292732ac66fa9d
updated: 2026-10-23
---

## Amaç
Arayüzün sunucuyla konuştuğu tek yer. Token yönetimi, JSON ayrıştırma, Türkçe hata mesajları, snake_case → camelCase. İstekler göreli `/api/...` yoluna gider (geliştirmede Vite proxy, yayında Vercel); CORS gerekmez.

## Public API
- `readToken() / writeToken(token|null)` — localStorage (gizli sekmede sessizce düşer)
- `userFromToken(token) -> User | null` — imza doğrulamadan JWT içeriği; sunucuya ulaşılamazken oturumu korumak için
- `checkHealth() -> Promise<Health>` — `{online, authRequired, guestQuestionLimit}`; hiç fırlatmaz, ulaşılamazsa `online:false, authRequired:true`
- `signInWithGoogle(idToken) -> {token, user}` — token'ı yazar
- `fetchMe() -> Promise<User>`
- `askQuestion(question, conversationId, history=[]) -> Promise<ChatAnswer>` — boş yanıt hata sayılır; `ChatAnswer.remaining`
- `fetchQuota() -> Promise<Quota>` — `{limit, remaining}`
- `fetchConversations()`, `fetchConversation(id) -> Message[]` (kararlı id üretir), `deleteConversation(id)`
- Tipler: `ChatAnswer`, `Health`, `HistoryTurn`, `Quota`

## Hata Tipleri
- `ApiUnreachableError` — fetch başarısız; ya da `detail`'siz 502/503/504 veya gövdesiz 500 (proxy arkasında API kapalı / uyanıyor)
- `UnauthorizedError` — 401; token silinir, `atilim:unauthorized` olayı yayılır
- düz `Error` — sunucunun `detail` mesajı olduğu gibi

## Dikkat
- Token key: `'atilim-assistant-token'`
- `checkHealth` `request`'i kullanmaz (401 olayı yaymamalı)
