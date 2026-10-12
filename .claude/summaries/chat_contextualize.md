---
source: backend/atilim_assistant/chat/contextualize.py
hash: 344da2b9cc1920ea9d3b1347cdb1bd5a48409b5f
updated: 2026-10-12
---

## Amaç
Takip sorularını önceki turlar olmadan anlaşılır hale getirir. İkinci model çağrısını minimize eder.

## Public API
- `needs_context(question, history) -> bool` — modele gitmeden önce yeniden yazım gerekip gerekmediğini belirler
- `rewrite(question, history, model) -> str` — bağımsız soruya dönüştürür; başarısız olursa ham soruyu döner

## Kararlar
- `_MAX_STANDALONE_TERMS = 3` — 3'ten fazla içerik kelimesi → kendi başına anlaşılırdır
- `_PRONOUNS` frozenset — "onu, bunu, orada" gibi dönüşlü zamirler → her zaman bağlamlandır
- `DISCOURSE_OPENERS` frozenset — "peki, ya, yani, devam" → her zaman bağlamlandır
- Büyük harfle başlayan kelime (özel ad) → bağlamlandırma atla
- `_MAX_REWRITE_LENGTH = 200` — daha uzun yanıt → model yanıt vermeye çalışmış, ham soruya dön
