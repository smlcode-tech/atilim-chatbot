"""HTTP API'nin istek ve yanıt gövdeleri."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

MAX_QUESTION_LENGTH = 1000
# Misafirin gönderdiği geçmiş turların sınırları; uzun yanıtlar sunucuda yine kısaltılır.
MAX_HISTORY_TURNS = 20
MAX_HISTORY_TURN_LENGTH = 8000


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(max_length=MAX_HISTORY_TURN_LENGTH)]


class ChatRequest(BaseModel):
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
    title: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceLink]
    # Yanıt model tarafından üretilmedi, hazır yanıtlardan verildi.
    prepared: bool
    # Soru yanıtlanamadıysa kullanıcıya seçenek olarak sunulan yakın sorular.
    suggestions: list[str] = []
    # Geçmiş deposu kapalıysa boş kalır.
    conversation_id: str | None = None
    title: str | None = None
    # Bu sorudan sonra bugün kalan soru hakkı; sayaç tutulamıyorsa (depo yok ya da hata) boş.
    remaining: int | None = None


class HealthResponse(BaseModel):
    status: str
    # False ise giriş yapılandırılmamıştır; arayüz giriş ekranını atlar, sorular misafir olarak
    # yanıtlanır. True ise Google girişi sunulur; misafir olarak devam etmek de mümkündür.
    auth_required: bool
    # Misafirin IP başına günlük soru sınırı; giriş ekranında gösterilir.
    guest_question_limit: int


class QuotaResponse(BaseModel):
    # Günlük soru sınırı: giriş yapan kullanıcıya ya da misafire göre.
    limit: int
    # Bugün kalan hak; sayaç tutulamıyorsa boş (sınır da uygulanamaz).
    remaining: int | None


class GoogleSignInRequest(BaseModel):
    """Google Identity Services'in tarayıcıda ürettiği kimlik jetonu."""

    id_token: Annotated[str, StringConstraints(min_length=1, max_length=4096)]


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


class SignInResponse(BaseModel):
    token: str
    user: UserResponse


class ConversationSummaryResponse(BaseModel):
    id: str
    title: str
    updated_at: datetime


class TurnResponse(BaseModel):
    role: str
    content: str
    created_at: datetime
    sources: list[SourceLink] = []
    suggestions: list[str] = []


class ConversationResponse(BaseModel):
    id: str
    turns: list[TurnResponse]
