"""HTTP API'nin istek ve yanıt gövdeleri."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

MAX_QUESTION_LENGTH = 1000


class ChatRequest(BaseModel):
    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_LENGTH),
    ]


class SourceLink(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceLink]
    # Yanıt model tarafından üretilmedi, hazır yanıtlardan verildi.
    prepared: bool


class HealthResponse(BaseModel):
    status: str
