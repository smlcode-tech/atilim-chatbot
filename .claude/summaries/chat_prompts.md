---
source: backend/atilim_assistant/chat/prompts.py
hash: ef8755f58734bdd93793545331155f46301606f4
updated: 2026-10-12
---

## Amaç
Model için sistem talimatı ve soru şablonları.

## Public API
- `SYSTEM_PROMPT: str` — yanıt üretim talimatı (Türkçe, yalnızca BAĞLAM'a dayan)
- `CONTEXTUALIZE_PROMPT: str` — takip sorusu bağımstızlaştırma talimatı
- `build_prompt(question, documents) -> str` — "BAĞLAM:\n...\n\nSORU: ..." formatında birleştirir

## Dikkat
- Yanıt promptuna konuşma geçmişi verilmez (prompt injection riski); geçmiş yalnızca bağlamlandırma çağrısında kullanılır
