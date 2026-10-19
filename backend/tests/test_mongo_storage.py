"""Mongo depolarının gerçek bir sunucuya karşı sınanması.

Bellek-içi sahteler portun sözleşmesini kapsar ama Mongo sorgularının kendisini kapsamaz.
Bu dosya yalnızca MONGODB_URI verildiğinde çalışır; CI ve günlük geliştirme için gerekli
değildir.
"""

import os
from uuid import uuid4

import pytest

from atilim_assistant.domain import Citation, Turn
from atilim_assistant.storage.mongo import (
    MongoConversationRepository,
    MongoUserRepository,
    connect,
)

URI = os.environ.get("MONGODB_URI")
pytestmark = pytest.mark.skipif(not URI, reason="MONGODB_URI tanımlı değil")


@pytest.fixture
def db():
    database = connect(URI, f"atilim_test_{uuid4().hex}")
    yield database
    database.client.drop_database(database.name)
    database.client.close()


def test_a_returning_user_keeps_the_same_identity(db):
    users = MongoUserRepository(db)

    first = users.upsert("google-sub-1", "ogrenci@atilim.edu.tr", "Öğrenci")
    again = users.upsert("google-sub-1", "ogrenci@atilim.edu.tr", "Yeni Ad")

    assert first == again
    assert db.users.find_one({"_id": first})["name"] == "Yeni Ad"


def test_the_daily_counter_restarts_when_the_day_changes(db):
    users = MongoUserRepository(db)
    user_id = users.upsert("google-sub-1", "ogrenci@atilim.edu.tr", "Öğrenci")

    assert users.count_question(user_id, "2026-10-12") == 1
    assert users.count_question(user_id, "2026-10-12") == 2
    assert users.count_question(user_id, "2026-10-13") == 1


def test_a_guest_counter_is_created_on_the_first_question(db):
    users = MongoUserRepository(db)

    assert users.count_guest_question("adres-ozeti", "2026-10-12") == 1
    assert users.count_guest_question("adres-ozeti", "2026-10-12") == 2
    assert users.count_guest_question("adres-ozeti", "2026-10-13") == 1
    assert users.count_guest_question("baska-adres", "2026-10-13") == 1
    # Misafir sayaçları kullanıcılar koleksiyonuna yazılmaz.
    assert db.users.count_documents({}) == 0


def test_turns_round_trip_with_their_timestamps(db):
    conversations = MongoConversationRepository(db)
    conversation_id = conversations.start("user-1", "Bölüm başkanı kim?")
    sources = [Citation(title="Akademik Personel", url="https://www.atilim.edu.tr/x")]
    written = [
        Turn(role="user", content="Soru"),
        Turn(role="assistant", content="Yanıt", sources=sources),
        Turn(role="assistant", content="Bulamadım", suggestions=["Bölüm başkanı kim?"]),
    ]

    conversations.add_turns(conversation_id, "user-1", written)

    read = conversations.turns(conversation_id, "user-1")
    assert [(t.role, t.content, t.sources, t.suggestions) for t in read] == [
        (t.role, t.content, t.sources, t.suggestions) for t in written
    ]
    # tz_aware bağlantı sayesinde zaman damgaları saat dilimiyle birlikte döner.
    assert read[0].created_at.tzinfo is not None


def test_a_conversation_is_invisible_to_other_users(db):
    conversations = MongoConversationRepository(db)
    conversation_id = conversations.start("user-1", "Bölüm başkanı kim?")

    assert conversations.turns(conversation_id, "user-2") is None
    assert conversations.delete(conversation_id, "user-2") is False
    assert conversations.list_for("user-2") == []


def test_conversations_are_listed_most_recently_updated_first(db):
    conversations = MongoConversationRepository(db)
    first = conversations.start("user-1", "İlk")
    second = conversations.start("user-1", "İkinci")
    conversations.add_turns(first, "user-1", [Turn(role="user", content="Yeni soru")])

    assert [row.id for row in conversations.list_for("user-1")] == [first, second]
