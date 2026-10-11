"""FastAPI uygulaması: /api/health ve /api/chat uç noktaları."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from atilim_assistant.api.schemas import (
    MAX_QUESTION_LENGTH,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SourceLink,
)
from atilim_assistant.bootstrap import build_chat_service
from atilim_assistant.chat.service import ChatService
from atilim_assistant.config import get_settings

logger = logging.getLogger(__name__)

UNAVAILABLE_DETAIL = (
    "Asistan şu anda yanıt üretemiyor ve bu soru için hazır bir yanıt yok. "
    "Lütfen daha sonra tekrar deneyin."
)


def create_app(chat_service: ChatService | None = None) -> FastAPI:
    """`chat_service` verilmezse ayarlardan kurulur; testler kendi servislerini verir."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.chat_service = chat_service or build_chat_service(get_settings())
        yield

    app = FastAPI(title="Atılım Akademik Asistan API", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:
        detail = f"Soru 1-{MAX_QUESTION_LENGTH} karakter uzunluğunda bir metin olmalıdır."
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.get("/api/health")
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/api/chat")
    def chat(body: ChatRequest, request: Request) -> ChatResponse:
        service: ChatService = request.app.state.chat_service
        try:
            answer = service.answer(body.question)
        except Exception:
            logger.exception("Yanıt oluşturulamadı")
            raise HTTPException(status_code=502, detail=UNAVAILABLE_DETAIL)
        return ChatResponse(
            answer=answer.text,
            sources=[SourceLink(title=c.title, url=c.url) for c in answer.citations],
            prepared=answer.prepared,
        )

    return app
