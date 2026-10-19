---
source: frontend/src/api/client.ts
hash: 4628a0741585b1b8b4c5ece00fa06e99bf274716
updated: 2026-10-19
---

## Amaç
Tüm API çağrılarının merkezi sarmalayıcısı. Token yönetimi, JSON ayrıştırma, Türkçe hata mesajları.

## Public API
- `readToken() / writeToken(token|null)` — localStorage token yönetimi
- `checkHealth() -> Promise<boolean>`
- `signInWithGoogle(idToken) -> Promise<{token, user}>` — token'ı localStorage'a yazar
- `fetchMe() -> Promise<User>`
- `askQuestion(question, conversationId|null) -> Promise<ChatAnswer>`
- `fetchConversations() -> Promise<ConversationSummary[]>`
- `fetchConversation(id) -> Promise<Message[]>`
- `deleteConversation(id) -> Promise<void>`

## Hata Tipleri
- `ApiUnreachableError` — sunucuya hiç ulaşılamadı
- `UnauthorizedError` — 401; token temizlenir, `atilim:unauthorized` custom event tetiklenir

## Dikkat
- Token key: `'atilim-assistant-token'`
- 401 → `writeToken(null)` + custom event dispatch
- Vite proxy'si API kapalıyken JSON olmayan 5xx → `ApiUnreachableError`
- `snake_case` → `camelCase` dönüşümü manuel yapılır (`conversation_id` → `conversationId`)

## Misafir ve öneriler (2026-10-19)
- `askQuestion(question, conversationId, history=[])` — misafir geçmişini gönderir; `checkHealth` `guestQuestionLimit` döndürür; yanıt ve turlarda `suggestions`
