---
source: frontend/src/App.tsx
hash: 211132394b0d0774b5cb563e3ac445ad5e8f9bb6
updated: 2026-10-12
---

## Amaç
React kök bileşeni. Splash screen, auth durumu, drawer sidebar, Cmd+K kısayolu.

## Davranış
- `SPLASH_MIN_MS = 2200` — auth ne kadar hızlı biterse bitsin splash en az bu kadar görünür
- Auth tamamlanana kadar splash bekler (iki koşul: min süre + auth bitti)
- `user === null` → `<SignIn>`, giriş yapıldıysa → `<main>` ile tam arayüz
- `chatKey` state'i `Composer` ve konuşma değişimlerini sıfırlamak için kullanılır
- Cmd+K / Ctrl+K → yeni sohbet başlatır
- Drawer (mobil sidebar) `isDrawerOpen` state'i ile yönetilir

## Hook Bağımlılıkları
- `useTheme` — tema toggle
- `useAuth` — Google giriş
- `useConversations` — yan bar listesi
- `useChat` — mesaj durumu + API
