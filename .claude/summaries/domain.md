---
source: backend/atilim_assistant/domain.py
hash: c48191beccef11c9a92ea15c2457bf4d1300d717
updated: 2026-10-12
---

## Amaç
Katmanlar arasında taşınan tüm çekirdek veri tipleri. Dış bağımlılığı yok.

## Veri Sınıfları
- `Document(id, source_id, source_title, url, unit, category, title, text)` — indekslenen bilgi birimi
- `PreparedAnswer(source_id, source_title, url, questions, answer)` — model olmadan verilen hazır yanıt
- `SourceContent(documents, prepared_answers)` — bir sayfanın ayrıştırılmış çıktısı
- `Source(id, title, url, unit, category, parser)` — sayfa + ayrıştırıcı çifti
- `Citation(title, url)` — yanıttaki kaynak bağlantısı
- `Answer(text, citations, prepared=False)` — servis katmanının döndürdüğü yanıt
- `User(id, email, name)` — giriş yapmış kullanıcı
- `Turn(role, content, created_at)` — konuşmanın tek bir söz birimi; role: "user"|"assistant"
- `ConversationSummary(id, title, updated_at)` — yan bar listesi için; turları taşımaz

## Dikkat
Tüm sınıflar `frozen=True, slots=True` — immutable ve bellek verimli.
