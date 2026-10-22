---
source: frontend/src/hooks/useChat.ts
hash: a57174430e5870f18c19bcaabff241f16173f189
updated: 2026-10-22
---

## Amaç
Mesaj durumu ve API çağrılarını yöneten ana hook.

## Public API
- `useChat({onConversationChanged}) -> {messages, conversationId, isLoading, apiStatus, sendMessage, startNew, open}`
- `sendMessage(text)` — soruyu ekler, API'yi çağırır, yanıtı veya hatayı ekler
- `startNew()` — mesajları ve conversationId'yi temizler
- `open(id)` — mevcut konuşmayı yükler

## Önemli Davranışlar
- İlk `apiStatus` (`'checking'|'online'|'offline'`) `initialApiStatus` seçeneğiyle `useAuth`'un sağlık denetiminden gelir; `/api/health` ayrıca istenmez
- `ApiUnreachableError` → `apiStatus = 'offline'`; diğer hatalar → `'online'`
- Hata durumunda mesaj listesine `isError: true` ile ekler (throw değil)
- `sendMessage` içinde `isLoading` true iken tekrar çağrı engellenir
- `onConversationChanged` yalnızca `conversationId` ilk kez set edildiğinde çağrılır

## Misafir ve öneriler (2026-10-19)
- `sendsHistory` seçeneği: misafirde son 6 mesaj (sunucunun `history_turns`'ü) (hata ve `isLocal` hariç, 4000 karakter) soruyla gönderilir; `askAgain()` "Diğer" seçiminde yerel mesaj ekler
