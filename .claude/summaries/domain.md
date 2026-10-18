---
source: backend/atilim_assistant/domain.py
hash: 7db5f4ccc4e11af5085b197dd0ec13b8d5404153
updated: 2026-10-18
---

## Amaç
Katmanlar arasında taşınan tüm çekirdek veri tipleri. Dış bağımlılığı yok.

## Veri Sınıfları
- `Document(id, source_id, source_title, url, unit, category, title, text)` — indekslenen bilgi birimi
- `PreparedAnswer(source_id, source_title, url, questions, answer)` — model olmadan verilen hazır yanıt
- `SourceContent(documents, prepared_answers, records={})` — bir sayfanın ayrıştırılmış çıktısı; `records` katalog kayıtları ("courses", "staff")
- `Source(id, title, url, unit, category, parser)` — sayfa + ayrıştırıcı çifti
- `Citation(title, url)` — yanıttaki kaynak bağlantısı
- `ToolCall(id, name, arguments)` — modelin istediği araç; `arguments` JSON metni
- `Completion(content, tool_calls=[])` — modelin bir turu
- `Answer(text, citations, prepared=False)` — servis katmanının döndürdüğü yanıt
- `User(id, email, name)` — giriş yapmış kullanıcı
- `Turn(role, content, created_at)` — konuşmanın tek bir söz birimi; role: "user"|"assistant"
- `ConversationSummary(id, title, updated_at)` — yan bar listesi için; turları taşımaz

## Dikkat
Tüm sınıflar `frozen=True, slots=True` — immutable ve bellek verimli.
