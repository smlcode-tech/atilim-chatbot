---
source: backend/atilim_assistant/api/schemas.py
hash: 769377e68284cabcab531bafba39de5218890ed3
updated: 2026-11-03
---

## Amaç
HTTP API için tüm Pydantic istek/yanıt modelleri. Alan modelinden (`domain.py`) ayrıdır: sözleşme `frontend/src/api/client.ts` ile paylaşılır. Sınırlar burada doğrulanır, geçersiz istek modele ulaşmaz.

## Modeller
- `HistoryTurn` — `role: "user"|"assistant"` (system yok), `content` (≤ 8000 karakter)
- `ChatRequest` — `question` (1-1000, strip), `conversation_id?`, `history: list[HistoryTurn]` (≤ 20; yalnızca misafirde kullanılır)
- `ChatResponse` — `answer`, `sources: list[SourceLink]`, `prepared`, `suggestions=[]`, `conversation_id?`, `remaining: int | None` (bu sorudan sonra bugün kalan hak; sayaç yoksa boş)
- `SourceLink` — `title`, `url`
- `HealthResponse` — `status`, `auth_required`, `guest_question_limit`
- `QuotaResponse` — `limit`, `remaining: int | None`
- `GoogleSignInRequest` — `id_token` (1-4096)
- `UserResponse` — `id`, `email`, `name` (`google_sub` dışarı verilmez)
- `SignInResponse` — `token`, `user`
- `ConversationSummaryResponse` — `id`, `title`, `updated_at`
- `TurnResponse` — `role`, `content`, `created_at`, `sources=[]`, `suggestions=[]`
- `ConversationResponse` — `id`, `turns`

## Sabitler
- `MAX_QUESTION_LENGTH = 1000` (422 mesajında da kullanılır)
- `MAX_HISTORY_TURNS = 20`, `MAX_HISTORY_TURN_LENGTH = 8000`
