---
source: frontend/src/hooks/useChat.ts
hash: 105f913c3d5693a9d61c2a4a57747201776aeb2e
updated: 2026-10-19
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

## Misafir ve öneriler (2026-10-19)
- `sendsHistory` seçeneği: misafirde son 12 mesaj (hata ve `isLocal` hariç, 4000 karakter) soruyla gönderilir; `askAgain()` "Diğer" seçiminde yerel mesaj ekler
