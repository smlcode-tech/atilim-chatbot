import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from atilim_assistant.api import app as api_app
from atilim_assistant.api.app import create_app
from atilim_assistant.auth import AuthError, issue_token, read_token
from atilim_assistant.domain import User


@pytest.fixture
def client(users, settings):
    with TestClient(create_app(None, users, settings)) as client:
        yield client


def test_a_session_token_round_trips_the_signed_in_user(user, settings):
    token = issue_token(user, settings.jwt_secret.get_secret_value(), settings.jwt_ttl_hours)

    assert read_token(token, settings.jwt_secret.get_secret_value()) == user


def test_a_token_signed_with_another_secret_is_rejected(user, settings):
    token = issue_token(user, "baska-bir-secret-en-az-32-bayt-uzunlukta!", settings.jwt_ttl_hours)

    with pytest.raises(AuthError):
        read_token(token, settings.jwt_secret.get_secret_value())


def test_an_expired_token_is_rejected(user, settings):
    token = issue_token(user, settings.jwt_secret.get_secret_value(), ttl_hours=-1)

    with pytest.raises(AuthError):
        read_token(token, settings.jwt_secret.get_secret_value())


def test_signing_in_with_google_stores_the_user_and_returns_a_token(
    client, users, settings, monkeypatch
):
    monkeypatch.setattr(
        api_app,
        "verify_google_token",
        lambda *_: ("google-sub-9", "yeni@atilim.edu.tr", "Yeni Kişi"),
    )

    response = client.post("/api/auth/google", json={"id_token": "google-tarafindan-verilen"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": "google-sub-9",
        "email": "yeni@atilim.edu.tr",
        "name": "Yeni Kişi",
    }
    assert users.saved["google-sub-9"].email == "yeni@atilim.edu.tr"
    assert read_token(body["token"], settings.jwt_secret.get_secret_value()) == User(
        id="google-sub-9", email="yeni@atilim.edu.tr", name="Yeni Kişi"
    )


def test_a_rejected_google_token_does_not_create_a_user(client, users, monkeypatch):
    def refuse(*_):
        raise AuthError("Google oturumu doğrulanamadı.")

    monkeypatch.setattr(api_app, "verify_google_token", refuse)

    response = client.post("/api/auth/google", json={"id_token": "sahte"})

    assert response.status_code == 401
    assert users.saved == {}


def test_who_am_i_reports_the_signed_in_user(client, user, auth_token):
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})

    assert response.status_code == 200
    assert response.json() == {"id": user.id, "email": user.email, "name": user.name}


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer sahte-jeton"}, {"Authorization": "Basic abc"}],
)
def test_who_am_i_refuses_requests_without_a_valid_session(client, headers):
    assert client.get("/api/auth/me", headers=headers).status_code == 401


@pytest.mark.parametrize("secret", ["", "kisa-bir-anahtar"])
def test_sign_in_is_turned_off_without_a_strong_signing_key(service, users, settings, secret):
    """Anahtarsız giriş açık görünür ama her denemede 500 verirdi."""
    weak = settings.model_copy(update={"jwt_secret": SecretStr(secret)})
    with TestClient(create_app(service, users, weak)) as client:
        assert client.get("/api/health").json()["auth_required"] is False
        assert client.post("/api/auth/google", json={"id_token": "t"}).status_code == 503
