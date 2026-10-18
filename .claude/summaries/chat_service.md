---
source: backend/atilim_assistant/chat/service.py
hash: 539cb183421e86bfd6c36f13b3536aa15d712645
updated: 2026-10-18
---

## Amaç
Ana soru-cevap akışı. Model konuşma geçmişini doğrudan görür ve veriyi araçlarla (`chat/tools.py`) sorgular; model yanıt veremezse hazır yanıta düşer.

## Public API
- `ChatService(tools, model, prepared_answers, quota_cooldown_seconds=3600)`
- `ChatService.answer(question, history?) -> Answer` — hem model hem hazır yanıt yoksa modelin hatasını yükseltir

## Akış
1. `tools.correct(question)` — yanlış yazılmış ders kodu düzeltilir ("MATF276" → "MATH276")
1b. Soru bir hazır yanıt kalıbıyla birebir aynıysa (`PreparedAnswerMatcher.exact`, ör. seçilen öneri) model çağrılmadan hazır yanıt döner
2. Soğuma yoksa `_converse`: sistem promptu + geçmiş (tur başı 1500 karakter) + soru → `model.complete(messages, DEFINITIONS)`; araç çağrıları çalıştırılır, sonuçlar `tool` mesajı olarak eklenir
3. Yanıt `NO_ANSWER` ile başlıyorsa `_with_suggestions`: `tools.suggest` ile en yakın 5 yanıtlı soru `Answer.suggestions`'a konur, metin `SUGGESTIONS_INTRO` olur (yakın soru yoksa model metni kalır)
4. Model hata verirse `_note_failure` + hazır yanıt (ham soruyla eşleştirme); yoksa hata yükselir

## Önemli Kısıtlamalar
- Hazır yanıtlar yalnızca yedek: model çalışırken her soru modele gider
- `_MAX_TOOL_ROUNDS = 4` — son turda araç verilmez, model eldekiyle yanıtlamak zorunda
- Kaynaklar (citations) çağrılan araçların döndürdüğü sayfalardır; yanıt `NO_ANSWER` ile başlıyorsa kaynak gösterilmez
- `_TRANSIENT_COOLDOWN_SECONDS = 60`; kota hatasında (`429`, `RESOURCE_EXHAUSTED`) `quota_cooldown_seconds`
- Soğuma sırasında önce hazır yanıt denenir; kota soğumasında hazır yanıt yoksa model çağrılmadan hata
