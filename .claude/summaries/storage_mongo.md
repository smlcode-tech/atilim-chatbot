---
source: backend/atilim_assistant/storage/mongo.py
hash: d422c85a2d0395a2b134983fcbf7cee5188ba9d2
updated: 2026-10-23
---

## Amaç
MongoDB üzerinde kullanıcı, günlük soru sayacı ve konuşma kalıcılığı.

## Public API
- `connect(uri, database) -> Database` — kısa zaman aşımlı istemci + indeksler; indeks kurulamazsa (Mongo uyuyor) yalnızca kaydeder, depolar yine kurulur
- `MongoUserRepository(db)`:
  - `upsert(google_sub, email, name) -> str`
  - `count_question(user_id, day) -> int` — artırır; kullanıcı kaydı yoksa oluşturmaz, 1 döner
  - `count_guest_question(guest_key, day) -> int` — `guest_quotas`'ta upsert
  - `questions_asked(user_id, day)` / `guest_questions_asked(guest_key, day)` — yalnızca okur (`/api/quota`)
  - `uncount_question(user_id, day)` / `uncount_guest_question(guest_key, day)` — yanıtlanamayan soruyu geri düşer
- `MongoConversationRepository(db)` — `start()`, `add_turns()`, `turns()` (yok/başkasının → None), `list_for()`, `delete()` (→ bool)

## Önemli Kısıtlamalar
- Belge kimlikleri ObjectId değil `uuid4().hex` — geçersiz kimlik 404 verir, 500 değil
- `_MAX_TURNS = 100` — aşınca en eski turlar `$slice` ile düşer
- `_MAX_LISTED = 50` — listelenen en çok konuşma
- `_RETENTION_DAYS = 90` — konuşmalarda TTL indeksi
- `_GUEST_QUOTA_RETENTION_DAYS = 2` — `guest_quotas` TTL (`quota_updated_at`)
- Sayaç (`_count`) tek atomik pipeline: gün belgede (`quota_day`), değişmişse 1'den başlar; gece sıfırlama işi yok
- `_asked` başka güne ait sayacı 0 sayar, yazmaz; `_uncount` yalnızca aynı gün ve > 0 ise azaltır
- `serverSelectionTimeoutMS=5000`, `connectTimeoutMS=5000`, `maxPoolSize=5` (Render uykudan kalkarken asılı kalmasın)
- Turlar `sources` ve `suggestions` da saklar; eski belgelerde eksik alanlar varsayılana düşer
