"""HTTP API'nin istek ve yanıt gövdeleri."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

MAX_QUESTION_LENGTH = 1000


class ChatRequest(BaseModel):
    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_LENGTH),
    ]
    # Boşsa yeni bir konuşma açılır ve kimliği yanıtta döner.
    conversation_id: str | None = None


class SourceLink(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceLink]
    # Yanıt model tarafından üretilmedi, hazır yanıtlardan verildi.
    prepared: bool
    # Geçmiş deposu kapalıysa boş kalır.
    conversation_id: str | None = None
    title: str | None = None


class HealthResponse(BaseModel):
    status: str


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


class ConversationResponse(BaseModel):
    id: str
    turns: list[TurnResponse]
