---
source: frontend/src/hooks/useChat.ts
hash: 896bbc689a9823ff5e6791e502db464e116ba552
updated: 2026-10-12
---

## Amaç
Mesaj durumu ve API çağrılarını yöneten ana hook.

## Public API
- `useChat({onConversationChanged}) -> {messages, conversationId, isLoading, apiStatus, sendMessage, startNew, open}`
- `sendMessage(text)` — soruyu ekler, API'yi çağırır, yanıtı veya hatayı ekler
- `startNew()` — mesajları ve conversationId'yi temizler
- `open(id)` — mevcut konuşmayı yükler

## Önemli Davranışlar
- Başlangıçta `checkHealth()` çağrısı → `apiStatus: 'checking'|'online'|'offline'`
- `ApiUnreachableError` → `apiStatus = 'offline'`; diğer hatalar → `'online'`
- Hata durumunda mesaj listesine `isError: true` ile ekler (throw değil)
- `sendMessage` içinde `isLoading` true iken tekrar çağrı engellenir
- `onConversationChanged` yalnızca `conversationId` ilk kez set edildiğinde çağrılır
