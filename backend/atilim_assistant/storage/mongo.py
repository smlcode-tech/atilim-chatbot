"""MongoDB üzerinde kullanıcı ve konuşma depoları.

Belge kimlikleri ObjectId değil uuid4 metnidir: geçersiz bir kimlik doğrulama hatası yerine
yalnızca "bulunamadı" sonucu verir.
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from atilim_assistant.domain import Citation, ConversationSummary, Turn

logger = logging.getLogger(__name__)

# Tek bir konuşmanın sınırsız büyümesi ücretsiz kümenin alanını tüketir.
_MAX_TURNS = 100
_MAX_LISTED = 50
# Dokunulmayan konuşmalar bu süre sonunda kendiliğinden silinir.
_RETENTION_DAYS = 90


def connect(uri: str, database: str) -> Database:
    """Bağlantıyı kurar ve indeksleri hazırlar.

    `MongoClient` kurulum sırasında ağa çıkmaz; ilk işlemde bağlanır. Render ücretsiz katmanı
    uykudan kalkarken varsayılan 30 saniyelik sunucu seçimi isteği askıda bırakacağı için
    zaman aşımları kısa tutulur.
    """
    client: MongoClient = MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        maxPoolSize=5,
        tz_aware=True,
        appname="atilim-assistant",
    )
    db = client[database]
    # İndeks kurulumu açılışta ağa çıkan tek işlemdir. Mongo o an ulaşılamazsa depolar yine
    # kurulur: istemci sonraki işlemlerde yeniden bağlanır, giriş ve geçmiş kendiliğinden döner.
    # Burada hata fırlatmak asistanı süreç yeniden başlayana kadar misafir kipinde bırakırdı.
    try:
        db.users.create_index([("google_sub", ASCENDING)], unique=True)
        db.conversations.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])
        db.conversations.create_index(
            [("updated_at", ASCENDING)], expireAfterSeconds=_RETENTION_DAYS * 86400
        )
    except PyMongoError:
        logger.exception("MongoDB indeksleri kurulamadı; bağlantı sonraki işlemlerde denenecek")
    return db


class MongoUserRepository:
    def __init__(self, db: Database) -> None:
        self._users = db.users
        # Misafir sayaçları kullanıcılardan ayrı tutulur; kullanıcı listesi kirlenmez.
        self._guest_quotas = db.guest_quotas

    def upsert(self, google_sub: str, email: str, name: str) -> str:
        existing = self._users.find_one_and_update(
            {"google_sub": google_sub},
            {
                "$set": {"email": email, "name": name, "seen_at": datetime.now(UTC)},
                "$setOnInsert": {"_id": uuid4().hex, "created_at": datetime.now(UTC)},
            },
            upsert=True,
            return_document=True,
        )
        return existing["_id"]

    def count_question(self, user_id: str, day: str) -> int:
        return _count(self._users, user_id, day, upsert=False)

    def count_guest_question(self, guest_key: str, day: str) -> int:
        # Misafirin önceden kaydı yoktur; sayaç belgesi ilk soruda oluşur.
        return _count(self._guest_quotas, guest_key, day, upsert=True)


def _count(collection: Collection, key: str, day: str, upsert: bool) -> int:
    # Tek bir atomik işlemde ya artır ya sıfırla: okuyup sonra yazmak eşzamanlı
    # isteklerde sayacı eksik bırakırdı.
    document = collection.find_one_and_update(
        {"_id": key},
        [
            {
                "$set": {
                    "quota_day": day,
                    "quota_count": {
                        "$cond": [
                            {"$eq": ["$quota_day", day]},
                            {"$add": [{"$ifNull": ["$quota_count", 0]}, 1]},
                            1,
                        ]
                    },
                }
            }
        ],
        upsert=upsert,
        return_document=True,
    )
    return 1 if document is None else document["quota_count"]


class MongoConversationRepository:
    def __init__(self, db: Database) -> None:
        self._conversations = db.conversations

    def start(self, user_id: str, title: str) -> str:
        now = datetime.now(UTC)
        conversation_id = uuid4().hex
        self._conversations.insert_one(
            {
                "_id": conversation_id,
                "user_id": user_id,
                "title": title,
                "turns": [],
                "created_at": now,
                "updated_at": now,
            }
        )
        return conversation_id

    def add_turns(self, conversation_id: str, user_id: str, turns: list[Turn]) -> None:
        self._conversations.update_one(
            {"_id": conversation_id, "user_id": user_id},
            {
                "$push": {"turns": {"$each": [_as_document(t) for t in turns], "$slice": -_MAX_TURNS}},
                "$set": {"updated_at": datetime.now(UTC)},
            },
        )

    def turns(self, conversation_id: str, user_id: str) -> list[Turn] | None:
        document = self._conversations.find_one(
            {"_id": conversation_id, "user_id": user_id}, {"turns": 1}
        )
        if document is None:
            return None
        return [_as_turn(turn) for turn in document["turns"]]

    def list_for(self, user_id: str) -> list[ConversationSummary]:
        documents = (
            self._conversations.find({"user_id": user_id}, {"title": 1, "updated_at": 1})
            .sort("updated_at", DESCENDING)
            .limit(_MAX_LISTED)
        )
        return [
            ConversationSummary(
                id=document["_id"], title=document["title"], updated_at=document["updated_at"]
            )
            for document in documents
        ]

    def delete(self, conversation_id: str, user_id: str) -> bool:
        result = self._conversations.delete_one({"_id": conversation_id, "user_id": user_id})
        return result.deleted_count == 1


def _as_document(turn: Turn) -> dict:
    return {
        "role": turn.role,
        "content": turn.content,
        "created_at": turn.created_at,
        "sources": [{"title": s.title, "url": s.url} for s in turn.sources],
        "suggestions": turn.suggestions,
    }


def _as_turn(document: dict) -> Turn:
    return Turn(
        role=document["role"],
        content=document["content"],
        created_at=document["created_at"],
        # Bu alan eklenmeden önce kaydedilen turlarda yoktur.
        sources=[Citation(**source) for source in document.get("sources", [])],
        suggestions=document.get("suggestions", []),
    )
