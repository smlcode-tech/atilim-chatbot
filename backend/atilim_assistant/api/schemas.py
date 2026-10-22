"""HTTP API'nin istek ve yanıt gövdeleri.

Alan modelinden (`domain.py`) ayrı tutulur: API sözleşmesi arayüzle (`frontend/src/api/
client.ts`) paylaşılır ve iç modeldeki bir değişiklik onu habersizce bozmamalıdır. Sınırlar
burada doğrulanır, böylece geçersiz istek modele ve kotaya hiç ulaşmaz.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

# Soru uzunluğu sınırı; hata mesajında da kullanılır (`app.invalid_request`).
MAX_QUESTION_LENGTH = 1000
# Misafirin gönderdiği geçmiş turların sınırları; uzun yanıtlar sunucuda yine kısaltılır.
MAX_HISTORY_TURNS = 20
MAX_HISTORY_TURN_LENGTH = 8000


class HistoryTurn(BaseModel):
    """Misafirin tarayıcıdan gönderdiği bir önceki tur. Rol yalnızca user/assistant olabilir:
    istemci "system" rolüyle modele talimat sokamamalıdır."""

    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(max_length=MAX_HISTORY_TURN_LENGTH)]


class ChatRequest(BaseModel):
    """`POST /api/chat` gövdesi."""

    # Baştaki/sondaki boşluk atılır; yalnızca boşluktan oluşan soru geçersizdir.
    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_LENGTH),
    ]
    # Boşsa yeni bir konuşma açılır ve kimliği yanıtta döner.
    conversation_id: str | None = None
    # Misafirin geçmişi sunucuda tutulmaz; takip soruları için sohbetin önceki turlarını
    # tarayıcı gönderir. Giriş yapan kullanıcıda yok sayılır, geçmiş depodan okunur.
    history: Annotated[list[HistoryTurn], Field(max_length=MAX_HISTORY_TURNS)] = []


class SourceLink(BaseModel):
    """Yanıtın altında gösterilen kaynak sayfa bağlantısı."""

    title: str
    url: str


class ChatResponse(BaseModel):
    """`POST /api/chat` yanıtı."""

    answer: str
    sources: list[SourceLink]
    # Yanıt model tarafından üretilmedi, hazır yanıtlardan verildi.
    prepared: bool
    # Soru yanıtlanamadıysa kullanıcıya seçenek olarak sunulan yakın sorular.
    suggestions: list[str] = []
    # Geçmiş deposu kapalıysa boş kalır.
    conversation_id: str | None = None
    # Yalnızca bu soruyla yeni konuşma açıldığında dolu: konuşmaya verilen başlık. (Arayüz
    # şu an kullanmıyor; yan barı listeyi yeniden çekerek günceller.)
    title: str | None = None
    # Bu sorudan sonra bugün kalan soru hakkı; sayaç tutulamıyorsa (depo yok ya da hata) boş.
    remaining: int | None = None


class HealthResponse(BaseModel):
    """`GET /api/health` yanıtı; arayüz açılışta bununla giriş ekranını ayarlar."""

    status: str
    # False ise giriş yapılandırılmamıştır; arayüz giriş ekranını atlar, sorular misafir olarak
    # yanıtlanır. True ise Google girişi sunulur; misafir olarak devam etmek de mümkündür.
    auth_required: bool
    # Misafirin IP başına günlük soru sınırı; giriş ekranında gösterilir.
    guest_question_limit: int


class QuotaResponse(BaseModel):
    """`GET /api/quota` yanıtı; arayüz kalan hakkı soru sormadan önce de gösterebilsin."""

    # Günlük soru sınırı: giriş yapan kullanıcıya ya da misafire göre.
    limit: int
    # Bugün kalan hak; sayaç tutulamıyorsa boş (sınır da uygulanamaz).
    remaining: int | None


class GoogleSignInRequest(BaseModel):
    """Google Identity Services'in tarayıcıda ürettiği kimlik jetonu."""

    # Üst sınır, doğrulamaya gitmeden önce aşırı büyük gövdeleri reddeder; gerçek jetonlar
    # bunun çok altındadır.
    id_token: Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class UserResponse(BaseModel):
    """Arayüzde gösterilen kullanıcı bilgisi; Google kimliği (`google_sub`) dışarı verilmez."""

    id: str
    email: str
    name: str


class SignInResponse(BaseModel):
    """Giriş sonucu: sonraki isteklerde `Authorization: Bearer` ile gönderilecek oturum jetonu."""

    token: str
    user: UserResponse


class ConversationSummaryResponse(BaseModel):
    """Yan bardaki bir konuşma; turlar listede taşınmaz, liste hafif kalır."""

    id: str
    title: str
    updated_at: datetime


class TurnResponse(BaseModel):
    """Kaydedilmiş bir tur. Kaynaklar ve öneriler de saklanır ki eski konuşma açıldığında
    yanıt ilk göründüğü gibi görünsün."""

    role: str
    content: str
    created_at: datetime
    sources: list[SourceLink] = []
    suggestions: list[str] = []


class ConversationResponse(BaseModel):
    """`GET /api/conversations/{id}` yanıtı: konuşmanın tüm turları."""

    id: str
    turns: list[TurnResponse]
