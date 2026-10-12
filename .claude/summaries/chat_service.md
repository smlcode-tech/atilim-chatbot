---
source: backend/atilim_assistant/chat/service.py
hash: e84ce4071d99821960bddb44dee2323e500533fa
updated: 2026-10-12
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
- `_standalone()`: `needs_context()` False dönerse modele ikinci çağrı yapılmaz
- Bağlamlandırma hatası ham soruyla devam ettirir (kota koruması için)
