---
source: backend/atilim_assistant/api/schemas.py
hash: 884d901131420221639e5825c76ba3e6079c94b0
updated: 2026-10-12
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
