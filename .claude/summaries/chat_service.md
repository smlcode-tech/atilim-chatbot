---
source: backend/atilim_assistant/chat/service.py
hash: a67f8693f4432c75b2baf3f6d01ba1909fd3f123
updated: 2026-10-17
---

## Amaç
Ana soru-cevap akışı. Modeli çağırır, hata durumunda hazır yanıta düşer.

## Public API
- `ChatService(retriever, model, prepared_answers, quota_cooldown_seconds=3600)`
- `ChatService.answer(question, history?) -> Answer` — hem model hem hazır yanıt yoksa modelin hatasını yükseltir

## Önemli Kısıtlamalar
- `_TRANSIENT_COOLDOWN_SECONDS = 60` — geçici hatada 60 sn bekleme
- `_QUOTA_MARKERS = ("RESOURCE_EXHAUSTED", "429")` — kota hatasında `quota_cooldown_seconds` (3600 sn default) bekleme
- Soğuma sırasında yalnızca hazır yanıtı olan sorular yanıtlanır
- `_standalone()`: geçmiş varsa ve soğuma yoksa soru her zaman `rewrite()` ile yeniden yazılır
- Bağlamlandırma hatası ham soruyla devam ettirir (kota koruması için)
