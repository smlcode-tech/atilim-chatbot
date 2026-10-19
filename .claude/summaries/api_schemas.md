---
source: backend/atilim_assistant/api/schemas.py
hash: 2ecf899ff46fb02ef13e6a2c7b1f8bd2a2b24b8b
updated: 2026-10-19
---

## Amaç
HTTP API için tüm Pydantic istek/yanıt modelleri.

## Modeller
- `ChatRequest` — `question` (1-1000 karakter, strip), `conversation_id: str | None`
- `ChatResponse` — `answer`, `sources: list[SourceLink]`, `prepared: bool`, `conversation_id?`, `title?`
- `SourceLink` — `title`, `url`
- `GoogleSignInRequest` — `id_token` (1-4096 karakter)
- `SignInResponse` — `token`, `user: UserResponse`
- `UserResponse` — `id`, `email`, `name`
- `ConversationSummaryResponse` — `id`, `title`, `updated_at: datetime`
- `ConversationResponse` — `id`, `turns: list[TurnResponse]`
- `TurnResponse` — `role`, `content`, `created_at: datetime`
- `HealthResponse` — `status`

## Sabitler
- `MAX_QUESTION_LENGTH = 1000`

## Misafir ve öneriler (2026-10-19)
- `ChatRequest.history: list[HistoryTurn]` (en çok 20 tur, tur başı 8000 karakter) — yalnızca misafirde kullanılır; `HealthResponse.guest_question_limit`; `ChatResponse`/`TurnResponse.suggestions`
