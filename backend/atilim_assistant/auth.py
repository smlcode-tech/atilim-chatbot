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

# Google kimlik jetonlarının `iss` alanı bu iki biçimden biri olabilir (Google belgesi).
_GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
# Oturum jetonunu yalnızca bu sunucu üretir ve doğrular; ortak gizli anahtarlı HS256 yeterlidir.
_SESSION_ALGORITHM = "HS256"

# Google'ın imza anahtarları; istemci anahtar kümesini 5 dakika önbellekte tutar
# (PyJWT varsayılanı), her girişte yeniden indirilmez.
_google_keys = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")


class AuthError(Exception):
    """Kimlik doğrulanamadı. HTTP'den bağımsızdır; 401'e API katmanı çevirir."""


def verify_google_token(id_token: str, client_id: str) -> tuple[str, str, str]:
    """Google kimlik jetonunu doğrular; (google_sub, email, name) döndürür.

    İmza, alıcı (`audience`: yalnızca bizim istemci kimliğimiz için üretilmiş jeton), yayıncı
    ve süre denetlenir. Doğrulanmamış e-posta reddedilir: adres kullanıcı kaydına ve oturum
    jetonuna yazılır, sahibi kanıtlanmamış bir adres başkasınınki olabilir. Ayrıntılı hata
    kullanıcıya gösterilmez, yalnızca "doğrulanamadı" denir.
    """
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
    """Girişten sonra verilen oturum jetonu; `ttl_hours` sonra geçersizleşir."""
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
    """Oturum jetonunu doğrulayıp kullanıcıya çevirir; geçersiz ya da süresi dolmuşsa `AuthError`."""
    try:
        # Algoritma açıkça sabitlenir: jetonun kendi başlığındaki algoritmaya güvenmek, imzasız
        # ("none") ya da başka algoritmalı sahte jetonların kabul edilmesine yol açabilirdi.
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
    """Oturum jetonu yoksa soru misafir olarak sorulur ve None döner; giriş yapılandırılmamışsa
    (Google istemci kimliği ya da kullanıcı deposu yok) herkes misafirdir. Jeton gönderilmişse
    geçerli olmalıdır: süresi dolan oturum sessizce misafire düşmez."""
    if not request.app.state.auth_enabled:
        return None
    return _optional_user(request)


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
