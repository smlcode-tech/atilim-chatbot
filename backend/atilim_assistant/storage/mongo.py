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
# Yan barda listelenen konuşma sayısı; daha eskileri listede görünmez ama süre dolana kadar
# (`_RETENTION_DAYS`) saklanır.
_MAX_LISTED = 50
# Dokunulmayan konuşmalar bu süre sonunda kendiliğinden silinir.
_RETENTION_DAYS = 90
# Misafir sayacı yalnızca kendi günü için anlamlıdır; her IP için birikmemesi için silinir.
_GUEST_QUOTA_RETENTION_DAYS = 2


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
        db.guest_quotas.create_index(
            [("quota_updated_at", ASCENDING)],
            expireAfterSeconds=_GUEST_QUOTA_RETENTION_DAYS * 86400,
        )
    except PyMongoError:
        logger.exception("MongoDB indeksleri kurulamadı; bağlantı sonraki işlemlerde denenecek")
    return db


class MongoUserRepository:
    """`UserRepository` portunun MongoDB uygulaması: kullanıcı kayıtları ve günlük soru sayaçları.

    Girişli kullanıcının sayacı kendi belgesinde (`quota_day`, `quota_count`) durur; ayrı
    koleksiyon gerekmez ve kullanıcı silinince sayacı da gider.
    """

    def __init__(self, db: Database) -> None:
        self._users = db.users
        # Misafir sayaçları kullanıcılardan ayrı tutulur; kullanıcı listesi kirlenmez.
        self._guest_quotas = db.guest_quotas

    def upsert(self, google_sub: str, email: str, name: str) -> str:
        """Her girişte çağrılır; kullanıcıyı ilk girişte oluşturur ve kimliğini döndürür.

        Kullanıcı Google kimliğiyle (`google_sub`) bulunur, e-postayla değil: e-posta
        değişebilir, `sub` değişmez. Ad ve e-posta her girişte güncellenir; iç kimlik
        (`_id`) yalnızca oluşturulurken atanır ki verilen oturum jetonları geçerli kalsın.
        Tek atomik işlemdir: aynı anda iki giriş iki kayıt açamaz (`google_sub` tekil indeksi).
        """
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
        """Kullanıcının `day` günündeki soru sayacını artırır ve yeni değeri döndürür.

        Kayıt yoksa oluşturulmaz (`upsert=False`): kullanıcı belgesi yalnızca girişte açılır,
        sayaç yüzünden ad ve e-postası olmayan bir kullanıcı belgesi oluşmamalıdır.
        """
        count = _count(self._users, user_id, day, upsert=False)
        if count is None:
            # Jeton geçerli ama kullanıcı kaydı yok (ör. veritabanı değişti): sayaç tutulamaz.
            logger.warning("Kullanıcı kaydı bulunamadı, günlük sınır uygulanamıyor: %s", user_id)
            return 1
        return count

    def count_guest_question(self, guest_key: str, day: str) -> int:
        """Misafir için `count_question`; anahtar IP adresinin özetidir."""
        # Misafirin önceden kaydı yoktur; sayaç belgesi ilk soruda oluşur.
        return _count(self._guest_quotas, guest_key, day, upsert=True) or 1

    def questions_asked(self, user_id: str, day: str) -> int:
        """O gün sorulan soru sayısı, sayacı artırmadan; kalan hakkı göstermek için."""
        return _asked(self._users, user_id, day)

    def guest_questions_asked(self, guest_key: str, day: str) -> int:
        """Misafir için `questions_asked`."""
        return _asked(self._guest_quotas, guest_key, day)

    def uncount_question(self, user_id: str, day: str) -> None:
        """Yanıtlanamayan soruyu sayaçtan geri düşer (bkz. `app.chat`)."""
        _uncount(self._users, user_id, day)

    def uncount_guest_question(self, guest_key: str, day: str) -> None:
        """Misafir için `uncount_question`."""
        _uncount(self._guest_quotas, guest_key, day)


def _count(collection: Collection, key: str, day: str, upsert: bool) -> int | None:
    """Günlük sayacı artırır; gün değişmişse 1'den başlatır. Belge yoksa (ve `upsert`
    kapalıysa) None.

    Gün belgede saklanır, gece sayaçları sıfırlayan ayrı bir zamanlanmış iş gerekmez: yeni
    günün ilk sorusu sayacı kendisi sıfırlar.
    """
    # Tek bir atomik işlemde ya artır ya sıfırla: okuyup sonra yazmak eşzamanlı
    # isteklerde sayacı eksik bırakırdı. Bu yüzden `$cond` içeren bir güncelleme hattı
    # (pipeline) kullanılır; düz `$inc` gün değişimini bilemez.
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
                    "quota_updated_at": "$$NOW",
                }
            }
        ],
        upsert=upsert,
        return_document=True,
    )
    return None if document is None else document["quota_count"]


def _asked(collection: Collection, key: str, day: str) -> int:
    """Sayacın değeri, yalnızca okuyarak. Sayaç başka bir güne aitse 0 sayılır: `_count` gibi
    sıfırlamak burada yazma gerektirirdi, okuma ucu depoyu değiştirmemelidir."""
    document = collection.find_one({"_id": key}, {"quota_day": 1, "quota_count": 1})
    if document is None or document.get("quota_day") != day:
        return 0
    return document.get("quota_count", 0)


def _uncount(collection: Collection, key: str, day: str) -> None:
    """Sayacı bir azaltır; yalnızca sayaç hâlâ aynı günündeyse ve sıfırın üstündeyse.

    Soru gece yarısından hemen önce sorulup yanıt sonra hata verdiyse sayaç yeni güne geçmiş
    olabilir; o durumda yeni günün sayacından düşmek yanlış olurdu.
    """
    collection.update_one(
        {"_id": key, "quota_day": day, "quota_count": {"$gt": 0}}, {"$inc": {"quota_count": -1}}
    )


class MongoConversationRepository:
    """`ConversationRepository` portunun MongoDB uygulaması.

    Her konuşma, turlarını içinde taşıyan tek bir belgedir: bir konuşma her zaman bütün
    olarak okunur ve tur sayısı sınırlıdır (`_MAX_TURNS`), ayrı tur koleksiyonu gerekmez.
    Her sorgu `user_id` ile süzülür: kullanıcı yalnızca kendi konuşmalarına erişebilir.
    """

    def __init__(self, db: Database) -> None:
        self._conversations = db.conversations

    def start(self, user_id: str, title: str) -> str:
        """Boş bir konuşma açar ve kimliğini döndürür; turlar `add_turns` ile eklenir."""
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
        """Turları sona ekler; `$slice` ile yalnızca son `_MAX_TURNS` tur tutulur.

        `updated_at` da yenilenir: hem yan bar sırası hem süre dolumu (TTL indeksi) buna bakar,
        yani kullanılan konuşma silinmez.
        """
        result = self._conversations.update_one(
            {"_id": conversation_id, "user_id": user_id},
            {
                "$push": {"turns": {"$each": [_as_document(t) for t in turns], "$slice": -_MAX_TURNS}},
                "$set": {"updated_at": datetime.now(UTC)},
            },
        )
        if result.matched_count == 0:
            # Konuşma bu arada silinmiş ya da süresi dolmuş: turlar hiçbir yere yazılmadı.
            logger.warning("Turlar kaydedilemedi, konuşma bulunamadı: %s", conversation_id)

    def turns(self, conversation_id: str, user_id: str) -> list[Turn] | None:
        """Konuşmanın turları; konuşma yoksa ya da başkasınınsa None (boş liste değil, ki
        "bulunamadı" ile "henüz turu yok" ayrılabilsin)."""
        document = self._conversations.find_one(
            {"_id": conversation_id, "user_id": user_id}, {"turns": 1}
        )
        if document is None:
            return None
        return [_as_turn(turn) for turn in document["turns"]]

    def list_for(self, user_id: str) -> list[ConversationSummary]:
        """Kullanıcının konuşmaları, en son güncellenen önce. Yalnızca başlık ve tarih okunur;
        turlar okunmaz, liste büyük konuşmalarda da hafif kalır. (user_id, updated_at)
        indeksi bu sorgu içindir."""
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
        """Konuşmayı siler; silinecek konuşma yoksa ya da başkasınınsa False (API 404 verir)."""
        result = self._conversations.delete_one({"_id": conversation_id, "user_id": user_id})
        return result.deleted_count == 1


def _as_document(turn: Turn) -> dict:
    """`Turn`'ü Mongo belgesine çevirir; alan modeli pymongo'yu bilmesin diye dönüşüm burada."""
    return {
        "role": turn.role,
        "content": turn.content,
        "created_at": turn.created_at,
        "sources": [{"title": s.title, "url": s.url} for s in turn.sources],
        "suggestions": turn.suggestions,
    }


def _as_turn(document: dict) -> Turn:
    """`_as_document`'ın tersi; sonradan eklenen alanlar eski belgelerde eksik olabilir."""
    return Turn(
        role=document["role"],
        content=document["content"],
        created_at=document["created_at"],
        # Bu alan eklenmeden önce kaydedilen turlarda yoktur.
        sources=[Citation(**source) for source in document.get("sources", [])],
        suggestions=document.get("suggestions", []),
    )
