---
source: frontend/src/App.tsx
hash: c768557616a815826df34430c66b40fbbe9b12c9
updated: 2026-10-19
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

## Misafir ve öneriler (2026-10-19)
- Giriş ekranında "Misafir olarak devam et" (`continueAsGuest`); misafirde yan bar düğmesi giriş ekranına döner (giriş yapılandırılmamışsa gizli); `useChat({ sendsHistory: isGuest })`; öneri seçimi ve "Diğer" (`askAgain` + Composer `focusRequest`)
