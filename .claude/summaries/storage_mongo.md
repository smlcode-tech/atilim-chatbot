---
source: backend/atilim_assistant/storage/mongo.py
hash: 3ccbde68375d771139f28457b49d92478e54aaa7
updated: 2026-10-12
---

## Amaç
MongoDB üzerinde kullanıcı ve konuşma kalıcılığı.

## Public API
- `connect(uri, database) -> Database` — bağlantı + indeksleri hazırlar
- `MongoUserRepository(db)` — `upsert(google_sub, email, name) -> str`, `count_question(user_id, day) -> int`
- `MongoConversationRepository(db)` — `start()`, `add_turns()`, `turns()`, `list_for()`, `delete()`

## Önemli Kısıtlamalar
- Belge kimlikleri ObjectId değil `uuid4().hex` — geçersiz kimlik 404 verir, 500 değil
- `_MAX_TURNS = 100` — sınırı aşınca en eski turlar `$slice` ile düşer
- `_MAX_LISTED = 50` — kullanıcı başına listelenecek maks konuşma
- `_RETENTION_DAYS = 90` — TTL indeksi ile otomatik silme
- `count_question` tek atomik pipeline kullanır (okuma+yazma race condition önlemi)
- Render ücretsiz katman uykudan kalkarken timeout sorunları için `serverSelectionTimeoutMS=5000`
