---
source: frontend/src/App.tsx
hash: b4c30d038c777313fdc62b6c8a34080c16599afb
updated: 2026-10-23
---

## Amaç
React kök bileşeni: hook'ları birbirine bağlar, hangi ekranın görüneceğine karar verir (splash → giriş ya da sohbet). Hook'lar birbirini tanımaz; App geri çağrılarla haber taşır.

## Davranış
- `SPLASH_MIN_MS = 2200` — splash iki koşulla kalkar: en kısa süre doldu + oturum denetimi (`isChecking`) bitti; ref'lerle senkronize
- Sayfa denetim biter bitmez splash'in altında kurulur (Google düğmesi önceden yüklenir); giriş ↔ uygulama arasında `AnimatePresence` ile 0.2 sn geçiş
- `user === null` → `<SignIn>` (`guestLimit` gösterilir), aksi hâlde `<main>`
- `user` null olunca `startNew()` — çıkışta önceki sohbet ekranda kalmaz
- `chatKey` Composer'ı konuşma değişiminde sıfırlar; `composerFocus` "Diğer" seçilince odak ister
- Açık konuşma silinirse yeni sohbete geçilir
- Cmd+K / Ctrl+K → yeni sohbet; drawer `isDrawerOpen`

## Hook Bağımlılıkları
- `useTheme`, `useAuth` (`isGuest`, `canSignIn`, `guestQuestionLimit`, `apiStatus`)
- `useConversations(user !== null && !isGuest)`
- `useQuota(user?.id)` — kimlik değişince yeniden alınır
- `useChat({ onConversationChanged, sendsHistory: isGuest, onRemaining: setRemaining, onQuotaStale: refreshQuota, initialApiStatus })`

## Misafir
- Misafirde yan bar düğmesi giriş ekranına döner; giriş yapılandırılmamışsa gizli
- Composer `quota` gösterir; hakkı biten misafire giriş önerilir (`suggestsSignIn`)
