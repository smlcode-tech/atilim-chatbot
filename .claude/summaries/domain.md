---
source: backend/atilim_assistant/domain.py
hash: 9fae3825015db0288cc710671a2ba13837d8cf40
updated: 2026-10-23
---

## Amaç
Katmanlar arasında taşınan tüm çekirdek veri tipleri. Dış pakete (FastAPI, pymongo, openai, chromadb) bağlı değil; her katman kendi dış biçimine (HTTP gövdesi, Mongo belgesi, Chroma üst verisi) kendisi çevirir.

## Veri Sınıfları
- `Document(id, source_id, source_title, url, unit, category, title, text)` — indekslenen bilgi birimi; `title` sayfa içi bölüm başlığı (soru kalıbı belgelerinde kalıbın kendisi)
- `PreparedAnswer(source_id, source_title, url, questions, answer)` — model olmadan verilen hazır yanıt
- `SourceContent(documents, prepared_answers, records={})` — ayrıştırıcının çıktısı, ingest'in girdisi; `records` katalog kayıtları ("courses", "staff")
- `Source(id, title, url, unit, category, parser, local_content_path=None)` — sayfa + ayrıştırıcı; `local_content_path` verilirse içerik yerel dosyadan okunur
- `Citation(title, url)` — yanıttaki kaynak bağlantısı
- `ToolCall(id, name, arguments)` — `arguments` JSON metni
- `Completion(content, tool_calls=[])` — modelin bir turu
- `Answer(text, citations, prepared=False, suggestions=[])` — `ChatService` çıktısı; API `ChatResponse`'a çevirir
- `User(id, email, name)` — `id` uygulamanın kimliği, Google'ınki değil
- `Turn(role, content, created_at, sources=[], suggestions=[])` — role: "user"|"assistant"
- `ConversationSummary(id, title, updated_at)` — yan bar listesi; turları taşımaz

## Dikkat
Tüm sınıflar `frozen=True, slots=True` — paylaşılan nesne yolda değiştirilemez.
