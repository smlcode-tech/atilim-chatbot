"""Google ile giriş ve oturum jetonu.

Google'ın verdiği kimlik jetonu yalnızca giriş anında doğrulanır; sonrasında kendi jetonumuz
kullanılır, böylece her istek Google'a gitmez. Jeton kullanıcının kimliğini, e-postasını ve adını
taşır, dolayısıyla istek başına veritabanı okuması da gerekmez.
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient

from atilim_assistant.domain import User

_GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
_SESSION_ALGORITHM = "HS256"

_google_keys = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")


class AuthError(Exception):
    """Kimlik doğrulanamadı."""


def verify_google_token(id_token: str, client_id: str) -> tuple[str, str, str]:
    """Google kimlik jetonunu doğrular; (google_sub, email, name) döndürür."""
    try:
        key = _google_keys.get_signing_key_from_jwt(id_token).key
        claims = jwt.decode(id_token, key, algorithms=["RS256"], audience=client_id)
    except Exception as error:
        raise AuthError("Google oturumu doğrulanamadı.") from error

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise AuthError("Google oturumu doğrulanamadı.")
    if not claims.get("email_verified"):
        raise AuthError("Google hesabının e-posta adresi doğrulanmamış.")

    email = claims["email"]
    return claims["sub"], email, claims.get("name") or email


def issue_token(user: User, secret: str, ttl_hours: int) -> str:
    return jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "exp": datetime.now(UTC) + timedelta(hours=ttl_hours),
        },
        secret,
        algorithm=_SESSION_ALGORITHM,
    )


def read_token(token: str, secret: str) -> User:
    try:
        claims = jwt.decode(token, secret, algorithms=[_SESSION_ALGORITHM])
    except Exception as error:
        raise AuthError("Oturumun süresi dolmuş. Lütfen yeniden giriş yapın.") from error
    return User(id=claims["sub"], email=claims["email"], name=claims["name"])


def current_user(request: Request) -> User:
    """`Authorization: Bearer` başlığındaki oturum jetonunu çözer."""
    user = _optional_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Bu işlem için giriş yapmalısınız.")
    return user


def chat_user(request: Request) -> User | None:
    """Giriş yapılandırılmamışsa (Google istemci kimliği ya da kullanıcı deposu yok) soru misafir
    olarak sorulur ve None döner; yapılandırılmışsa giriş zorunludur."""
    if not request.app.state.auth_enabled:
        return None
    return current_user(request)


def _optional_user(request: Request) -> User | None:
    """Jeton yoksa None; varsa geçerli olmak zorundadır."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    secret = request.app.state.settings.jwt_secret.get_secret_value()
    try:
        return read_token(token, secret)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
