---
source: backend/atilim_assistant/chat/contextualize.py
hash: 58976d61a04653366e3fe42567aa340fa22d1f8c
updated: 2026-10-17
---

## Amaç
Takip sorularını önceki turlar olmadan anlaşılır hale getirir.

## Public API
- `rewrite(question, history, model) -> str` — bağımsız soruya dönüştürür; başarısız olursa ham soruyu döner

## Kararlar
- Geçmişi olan her soru yeniden yazılır (kapı `ChatService._standalone`'da: geçmiş yoksa ya da soğuma varsa atlanır)
- Eski `needs_context` sözcük kuralı kaldırıldı: eş anlamlı takip sorularını ("Bunlara nasıl ulaşırım?", "Listedekilerin numaraları?") kaçırıyordu
- `_MAX_TURN_CHARS = 500` — geçmiş turlar kırpılır; uzun listeler token kotasını harcamasın
- `_MAX_REWRITE_LENGTH = 200` — daha uzun yanıt → model yanıt vermeye çalışmış, ham soruya dön
