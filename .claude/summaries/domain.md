---
source: backend/atilim_assistant/domain.py
hash: 1b8ab807ccb62af1b6d17bc9b01251fe61b3ea3b
updated: 2026-10-20
---

## Amaç
Katmanlar arasında taşınan tüm çekirdek veri tipleri. Dış bağımlılığı yok.

## Veri Sınıfları
- `Document(id, source_id, source_title, url, unit, category, title, text)` — indekslenen bilgi birimi
- `PreparedAnswer(source_id, source_title, url, questions, answer)` — model olmadan verilen hazır yanıt
- `SourceContent(documents, prepared_answers, records={})` — bir sayfanın ayrıştırılmış çıktısı; `records` katalog kayıtları ("courses", "staff")
- `Source(id, title, url, unit, category, parser, local_content_path=None)` — sayfa + ayrıştırıcı çifti; `local_content_path` verilirse içerik siteden değil yerel dosyadan okunur
- `Citation(title, url)` — yanıttaki kaynak bağlantısı
- `ToolCall(id, name, arguments)` — modelin istediği araç; `arguments` JSON metni
- `Completion(content, tool_calls=[])` — modelin bir turu
- `Answer(text, citations, prepared=False, suggestions=[])` — servis katmanının döndürdüğü yanıt; `suggestions` yanıtlanamayan soruda önerilen yakın sorular
- `User(id, email, name)` — giriş yapmış kullanıcı
- `Turn(role, content, created_at, sources=[], suggestions=[])` — konuşmanın tek bir söz birimi; role: "user"|"assistant"; asistan turu kaynaklarını ve önerilerini taşır
- `ConversationSummary(id, title, updated_at)` — yan bar listesi için; turları taşımaz

## Dikkat
Tüm sınıflar `frozen=True, slots=True` — immutable ve bellek verimli.
