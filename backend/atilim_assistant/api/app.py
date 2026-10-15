"""FastAPI uygulaması: /api/health ve /api/chat uç noktaları."""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from atilim_assistant.api.schemas import (
    MAX_QUESTION_LENGTH,
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ConversationSummaryResponse,
    GoogleSignInRequest,
    HealthResponse,
    SignInResponse,
    SourceLink,
    TurnResponse,
    UserResponse,
)
from atilim_assistant.auth import (
    AuthError,
    chat_user,
    current_user,
    issue_token,
    verify_google_token,
)
from atilim_assistant.bootstrap import build_chat_service, build_conversation_store
from atilim_assistant.chat.service import ChatService
from atilim_assistant.config import Settings, get_settings
from atilim_assistant.domain import Turn, User
from atilim_assistant.ports import ConversationRepository, UserRepository

logger = logging.getLogger(__name__)

UNAVAILABLE_DETAIL = (
    "Asistan şu anda yanıt üretemiyor ve bu soru için hazır bir yanıt yok. "
    "Lütfen daha sonra tekrar deneyin."
)


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name)


def create_app(
    chat_service: ChatService | None = None,
    users: UserRepository | None = None,
    settings: Settings | None = None,
    conversations: ConversationRepository | None = None,
) -> FastAPI:
    """Verilmeyen bileşenler ayarlardan kurulur; testler kendi sahte nesnelerini verir."""
    injected = users is not None or conversations is not None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings or get_settings()
        app.state.chat_service = chat_service or build_chat_service(app.state.settings)
        app.state.users = users
        app.state.conversations = conversations
        if not injected:
            # Mongo'ya ulaşılamazsa asistan geçmişsiz çalışmaya devam eder. Burada hata
            # fırlatmak Render'da sağlık kontrolünü hiç geçirmez ve çalışan asistanı düşürür.
            try:
                app.state.users, app.state.conversations = build_conversation_store(
                    app.state.settings
                )
            except Exception:
                logger.exception("Konuşma geçmişi deposuna bağlanılamadı; geçmişsiz devam ediliyor")
        # Giriş kurulamıyorsa asistan kilitlenmez; sorular misafir olarak, geçmişsiz yanıtlanır.
        app.state.auth_enabled = bool(app.state.settings.google_client_id) and (
            app.state.users is not None
        )
        if not app.state.auth_enabled:
            logger.warning("Google girişi yapılandırılmamış; sorular misafir olarak yanıtlanıyor.")
        yield

    app = FastAPI(title="Atılım Akademik Asistan API", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        if any("question" in failure["loc"] for failure in error.errors()):
            detail = f"Soru 1-{MAX_QUESTION_LENGTH} karakter uzunluğunda bir metin olmalıdır."
        else:
            detail = "İstek geçersiz."
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.get("/api/health")
    def health(request: Request) -> HealthResponse:
        return HealthResponse(status="ok", auth_required=request.app.state.auth_enabled)

    @app.post("/api/auth/google")
    def sign_in(body: GoogleSignInRequest, request: Request) -> SignInResponse:
        settings: Settings = request.app.state.settings
        users: UserRepository | None = request.app.state.users
        if not settings.google_client_id or users is None:
            raise HTTPException(status_code=503, detail="Giriş şu anda kullanılamıyor.")
        try:
            google_sub, email, name = verify_google_token(
                body.id_token, settings.google_client_id
            )
        except AuthError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

        user = User(id=users.upsert(google_sub, email, name), email=email, name=name)
        token = issue_token(
            user, settings.jwt_secret.get_secret_value(), settings.jwt_ttl_hours
        )
        return SignInResponse(token=token, user=_user_response(user))

    @app.get("/api/auth/me")
    def me(user: User = Depends(current_user)) -> UserResponse:
        return _user_response(user)

    @app.post("/api/chat")
    def chat(
        body: ChatRequest, request: Request, user: User | None = Depends(chat_user)
    ) -> ChatResponse:
        service: ChatService = request.app.state.chat_service
        settings: Settings = request.app.state.settings
        # Misafirin geçmişi tutulmaz; konuşma kimliği de yalnızca giriş yapan kullanıcıya aittir.
        conversations: ConversationRepository | None = (
            request.app.state.conversations if user is not None else None
        )

        if user is not None:
            _check_daily_limit(request.app.state.users, user.id, settings.daily_question_limit)

        history: list[Turn] = []
        conversation_id = None
        if conversations is not None and user is not None:
            conversation_id, history = _resume(
                conversations, user.id, body.conversation_id, settings
            )

        try:
            answer = service.answer(body.question, history)
        except Exception:
            logger.exception("Yanıt oluşturulamadı")
            raise HTTPException(status_code=502, detail=UNAVAILABLE_DETAIL)

        title = None
        if conversations is not None and user is not None:
            if conversation_id is None:
                title = _title_from(body.question)
                conversation_id = conversations.start(user.id, title)
            # Kullanıcının yazdığı ham metin saklanır; bağlamlandırılmış hâli yalnızca aramada
            # kullanılır, geçmişte görünmemelidir.
            conversations.add_turns(
                conversation_id,
                user.id,
                [
                    Turn(role="user", content=body.question),
                    Turn(role="assistant", content=answer.text, sources=answer.citations),
                ],
            )

        return ChatResponse(
            answer=answer.text,
            sources=[SourceLink(title=c.title, url=c.url) for c in answer.citations],
            prepared=answer.prepared,
            conversation_id=conversation_id,
            title=title,
        )

    @app.get("/api/conversations")
    def list_conversations(
        request: Request, user: User = Depends(current_user)
    ) -> list[ConversationSummaryResponse]:
        conversations = _require_history(request)
        return [
            ConversationSummaryResponse(
                id=summary.id, title=summary.title, updated_at=summary.updated_at
            )
            for summary in conversations.list_for(user.id)
        ]

    @app.get("/api/conversations/{conversation_id}")
    def read_conversation(
        conversation_id: str, request: Request, user: User = Depends(current_user)
    ) -> ConversationResponse:
        turns = _require_history(request).turns(conversation_id, user.id)
        if turns is None:
            raise HTTPException(status_code=404, detail="Konuşma bulunamadı.")
        return ConversationResponse(
            id=conversation_id,
            turns=[
                TurnResponse(
                    role=t.role,
                    content=t.content,
                    created_at=t.created_at,
                    sources=[SourceLink(title=s.title, url=s.url) for s in t.sources],
                )
                for t in turns
            ],
        )

    @app.delete("/api/conversations/{conversation_id}", status_code=204)
    def delete_conversation(
        conversation_id: str, request: Request, user: User = Depends(current_user)
    ) -> None:
        if not _require_history(request).delete(conversation_id, user.id):
            raise HTTPException(status_code=404, detail="Konuşma bulunamadı.")

    return app


def _check_daily_limit(users: UserRepository | None, user_id: str, limit: int) -> None:
    """Sayaç tutulamıyorsa soru geçer: depo kesintisi asistanı durdurmamalı."""
    if users is None:
        return
    try:
        asked = users.count_question(user_id, datetime.now(UTC).date().isoformat())
    except Exception:
        logger.exception("Günlük soru sayacı güncellenemedi")
        return
    if asked > limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Günlük {limit} soru sınırına ulaştın. Asistan ücretsiz bir kota ile "
                "çalışıyor; yarın tekrar bekleriz."
            ),
        )


def _require_history(request: Request) -> ConversationRepository:
    conversations: ConversationRepository | None = request.app.state.conversations
    if conversations is None:
        raise HTTPException(status_code=503, detail="Konuşma geçmişi şu anda kullanılamıyor.")
    return conversations


def _resume(
    conversations: ConversationRepository,
    user_id: str,
    conversation_id: str | None,
    settings: Settings,
) -> tuple[str | None, list[Turn]]:
    """Süren konuşmanın son turlarını getirir; kimlik verilmemişse boş geçmiş döner."""
    if conversation_id is None:
        return None, []
    turns = conversations.turns(conversation_id, user_id)
    if turns is None:
        raise HTTPException(status_code=404, detail="Konuşma bulunamadı.")
    return conversation_id, turns[-settings.history_turns :]


def _title_from(question: str) -> str:
    return question if len(question) <= 60 else f"{question[:57].rstrip()}…"
