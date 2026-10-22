"""FastAPI uygulaması: /api/health ve /api/chat uç noktaları."""

import hashlib
import hmac
import logging
from collections.abc import Callable
from typing import TypeVar
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
    QuotaResponse,
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

T = TypeVar("T")

# HS256 için önerilen en kısa anahtar (RFC 7518, 3.2).
MIN_JWT_SECRET_BYTES = 32

HISTORY_UNAVAILABLE_DETAIL = "Konuşma geçmişi şu anda kullanılamıyor."

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
        # İmza anahtarı yoksa jeton üretilemez ve her giriş 500 verir; kısaysa jetonlar tahmin
        # edilebilir. Giriş açık görünüp çalışmamaktansa kapatılır.
        secret = app.state.settings.jwt_secret.get_secret_value()
        if app.state.auth_enabled and len(secret.encode()) < MIN_JWT_SECRET_BYTES:
            logger.error(
                "JWT_SECRET boş ya da %d bayttan kısa; Google girişi kapatıldı.",
                MIN_JWT_SECRET_BYTES,
            )
            app.state.auth_enabled = False
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
        return HealthResponse(
            status="ok",
            auth_required=request.app.state.auth_enabled,
            guest_question_limit=request.app.state.settings.guest_daily_question_limit,
        )

    @app.post("/api/auth/google")
    def sign_in(body: GoogleSignInRequest, request: Request) -> SignInResponse:
        settings: Settings = request.app.state.settings
        users: UserRepository | None = request.app.state.users
        if not request.app.state.auth_enabled or users is None:
            raise HTTPException(status_code=503, detail="Giriş şu anda kullanılamıyor.")
        try:
            google_sub, email, name = verify_google_token(
                body.id_token, settings.google_client_id
            )
        except AuthError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

        try:
            user_id = users.upsert(google_sub, email, name)
        except Exception as error:
            logger.exception("Kullanıcı kaydedilemedi")
            raise HTTPException(status_code=503, detail="Giriş şu anda kullanılamıyor.") from error
        user = User(id=user_id, email=email, name=name)
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

        users: UserRepository | None = request.app.state.users
        limit = _daily_limit(settings, user)
        if user is not None:
            counted = _check_daily_limit(
                lambda day: users.count_question(user.id, day),
                users,
                f"Günlük {settings.daily_question_limit} soru sınırına ulaştın. Asistan ücretsiz "
                "bir kota ile çalışıyor; yarın tekrar bekleriz.",
                settings.daily_question_limit,
            )
        else:
            guest = _guest_key(request)
            counted = _check_daily_limit(
                lambda day: users.count_guest_question(guest, day),
                users,
                f"Misafir olarak günlük {settings.guest_daily_question_limit} soru sınırına "
                "ulaştın. Google ile giriş yaparak sormaya devam edebilirsin.",
                settings.guest_daily_question_limit,
            )
        counted_day, asked = counted if counted is not None else (None, None)

        history: list[Turn] = []
        conversation_id = None
        if conversations is not None and user is not None:
            try:
                conversation_id, history = _resume(
                    conversations, user.id, body.conversation_id, settings
                )
            except HTTPException:
                raise
            except Exception:
                # Geçmiş okunamıyorsa soru geçmişsiz yanıtlanır; kaydetmek de denenmez, çünkü
                # depo büyük olasılıkla yazmayı da reddeder ve yanıt yine de verilmelidir.
                logger.exception("Konuşma geçmişi okunamadı; soru geçmişsiz yanıtlanıyor")
                conversations = None
        elif user is None:
            history = _last(
                [Turn(role=turn.role, content=turn.content) for turn in body.history],
                settings.history_turns,
            )

        try:
            answer = service.answer(body.question, history)
        except Exception:
            logger.exception("Yanıt oluşturulamadı")
            # Yanıtlanamayan soru günlük sınırdan düşülmez; kesinti sırasında yeniden deneyen
            # kullanıcı hiç yanıt almadan sınırına ulaşırdı.
            if counted_day is not None and users is not None:
                try:
                    if user is not None:
                        users.uncount_question(user.id, counted_day)
                    else:
                        users.uncount_guest_question(guest, counted_day)
                except Exception:
                    logger.exception("Günlük soru sayacı geri alınamadı")
            raise HTTPException(status_code=502, detail=UNAVAILABLE_DETAIL)

        title = None
        if conversations is not None and user is not None:
            # Yanıt üretildi ve kotadan düşüldü; kaydedilemedi diye kullanıcıya verilmemesi
            # boşa harcanmış bir soru olurdu.
            try:
                if conversation_id is None:
                    new_title = _title_from(body.question)
                    conversation_id = conversations.start(user.id, new_title)
                    title = new_title
                # Kullanıcının yazdığı ham metin saklanır; ders kodu düzeltilmiş hâli yalnızca
                # yanıtlamada kullanılır, geçmişte görünmemelidir.
                conversations.add_turns(
                    conversation_id,
                    user.id,
                    [
                        Turn(role="user", content=body.question),
                        Turn(
                            role="assistant",
                            content=answer.text,
                            sources=answer.citations,
                            suggestions=answer.suggestions,
                        ),
                    ],
                )
            except Exception:
                logger.exception("Konuşma kaydedilemedi; yanıt kaydedilmeden veriliyor")

        return ChatResponse(
            answer=answer.text,
            sources=[SourceLink(title=c.title, url=c.url) for c in answer.citations],
            prepared=answer.prepared,
            suggestions=answer.suggestions,
            conversation_id=conversation_id,
            title=title,
            remaining=None if asked is None else max(0, limit - asked),
        )

    @app.get("/api/quota")
    def quota(request: Request, user: User | None = Depends(chat_user)) -> QuotaResponse:
        """Bugün kalan soru hakkı; sayacı değiştirmez. Arayüz açılışta gösterir."""
        settings: Settings = request.app.state.settings
        users: UserRepository | None = request.app.state.users
        limit = _daily_limit(settings, user)
        if users is None:
            return QuotaResponse(limit=limit, remaining=None)
        day = datetime.now(UTC).date().isoformat()
        try:
            if user is not None:
                asked = users.questions_asked(user.id, day)
            else:
                asked = users.guest_questions_asked(_guest_key(request), day)
        except Exception:
            logger.exception("Günlük soru sayacı okunamadı")
            return QuotaResponse(limit=limit, remaining=None)
        return QuotaResponse(limit=limit, remaining=max(0, limit - asked))

    @app.get("/api/conversations")
    def list_conversations(
        request: Request, user: User = Depends(current_user)
    ) -> list[ConversationSummaryResponse]:
        summaries = _from_history(request, lambda store: store.list_for(user.id))
        return [
            ConversationSummaryResponse(
                id=summary.id, title=summary.title, updated_at=summary.updated_at
            )
            for summary in summaries
        ]

    @app.get("/api/conversations/{conversation_id}")
    def read_conversation(
        conversation_id: str, request: Request, user: User = Depends(current_user)
    ) -> ConversationResponse:
        turns = _from_history(request, lambda store: store.turns(conversation_id, user.id))
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
                    suggestions=t.suggestions,
                )
                for t in turns
            ],
        )

    @app.delete("/api/conversations/{conversation_id}", status_code=204)
    def delete_conversation(
        conversation_id: str, request: Request, user: User = Depends(current_user)
    ) -> None:
        if not _from_history(request, lambda store: store.delete(conversation_id, user.id)):
            raise HTTPException(status_code=404, detail="Konuşma bulunamadı.")

    return app


def _daily_limit(settings: Settings, user: User | None) -> int:
    if user is not None:
        return settings.daily_question_limit
    return settings.guest_daily_question_limit


def _check_daily_limit(
    count: Callable[[str], int], users: UserRepository | None, detail: str, limit: int
) -> tuple[str, int] | None:
    """`count` o günün sayacını artırıp döndürür. Sayaç tutulamıyorsa soru geçer: depo
    kesintisi asistanı durdurmamalı. Sayaç artırıldıysa günü (geri almak için) ve o günün
    soru sayısını döndürür."""
    if users is None:
        return None
    day = datetime.now(UTC).date().isoformat()
    try:
        asked = count(day)
    except Exception:
        logger.exception("Günlük soru sayacı güncellenemedi")
        return None
    if asked > limit:
        raise HTTPException(status_code=429, detail=detail)
    return day, asked


def _last(turns: list[Turn], count: int) -> list[Turn]:
    """Son `count` tur; `turns[-0:]` listenin tamamını verdiği için sıfır ayrıca ele alınır."""
    return turns[-count:] if count > 0 else []


def _guest_key(request: Request) -> str:
    """Misafirin sayaç anahtarı: istemci IP adresinin özeti; adresin kendisi saklanmaz."""
    address = _client_ip(request, request.app.state.settings.proxy_secret.get_secret_value())
    return hashlib.sha256(address.encode()).hexdigest()


def _client_ip(request: Request, proxy_secret: str) -> str:
    """İsteği gönderen istemcinin IP adresi.

    Arayüz `/api` isteklerini Vercel üzerinden iletir; Render'ın `X-Forwarded-For` sonuna
    eklediği adres o zaman Vercel'in çıkış adresidir ve misafirlerin hepsi birkaç sayacı
    paylaşır. Vercel istemci adresini kendi başlıklarına yazar (istemcinin gönderdiği aynı
    adlı başlıkların üzerine yazarak), ama Render'a doğrudan gelen biri de bu başlıkları
    uydurabilir. Bu yüzden onlara yalnızca Vercel'in eklediği ortak gizli `X-Proxy-Secret`
    doğruysa güvenilir.

    Aksi hâlde `X-Forwarded-For` başlığının son öğesi alınır: onu Render ekler. Baştaki
    öğeleri istemci kendisi yazabilir; onlara güvenmek her istekte farklı adres uydurarak
    sınırı aşmaya izin verirdi.
    """
    if proxy_secret and hmac.compare_digest(
        request.headers.get("X-Proxy-Secret", "").encode(), proxy_secret.encode()
    ):
        for header in ("X-Vercel-Forwarded-For", "X-Real-IP", "X-Forwarded-For"):
            address = request.headers.get(header, "").split(",")[0].strip()
            if address:
                return address
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[-1].strip() or (request.client.host if request.client else "")


def _from_history(request: Request, use: Callable[[ConversationRepository], T]) -> T:
    """Geçmiş deposuna bir işlem; depo kapalıysa ya da o an ulaşılamıyorsa 503 (500 değil):
    arayüz bunu "geçmiş kullanılamıyor" diye gösterir, sohbet sürer."""
    conversations: ConversationRepository | None = request.app.state.conversations
    if conversations is None:
        raise HTTPException(status_code=503, detail=HISTORY_UNAVAILABLE_DETAIL)
    try:
        return use(conversations)
    except Exception as error:
        logger.exception("Konuşma geçmişine ulaşılamadı")
        raise HTTPException(status_code=503, detail=HISTORY_UNAVAILABLE_DETAIL) from error


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
    return conversation_id, _last(turns, settings.history_turns)


def _title_from(question: str) -> str:
    return question if len(question) <= 60 else f"{question[:57].rstrip()}…"
