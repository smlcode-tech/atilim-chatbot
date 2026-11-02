import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from atilim_assistant.api.app import create_app
from atilim_assistant.auth import issue_token
from atilim_assistant.domain import User
from tests.conftest import tool_call


@pytest.fixture
def other_client(service, users, settings, conversations):
    """Aynı depoyu paylaşan ikinci bir kullanıcı."""
    token = issue_token(
        User(id="google-sub-2", email="baskasi@atilim.edu.tr", name="Başkası"),
        settings.jwt_secret.get_secret_value(),
        settings.jwt_ttl_hours,
    )
    app = create_app(service, users, settings, conversations)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        yield client


def test_the_first_question_opens_a_conversation_titled_after_it(client):
    response = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"})

    body = response.json()
    assert body["conversation_id"] is not None
    assert body["title"] == "Bölüm başkanı kim?"


def test_a_long_first_question_is_shortened_into_a_title(client):
    question = "Yazılım Mühendisliği bölümünde hangi dersler zorunlu olarak okutuluyor acaba?"

    title = client.post("/api/chat", json={"question": question}).json()["title"]

    assert len(title) <= 60
    assert title.endswith("…")
    assert question.startswith(title[:-1])


def test_following_up_appends_to_the_same_conversation(client, model):
    # Her soruda model bir araç çağırır; yanıtların kaynağı aracın getirdiği sayfadır.
    model.script = [tool_call("belge_ara", sorgu="bölüm başkanı")]
    started = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"}).json()

    model.script = [tool_call("belge_ara", sorgu="hocalar")]
    second = client.post(
        "/api/chat",
        json={"question": "Hocalar kimler?", "conversation_id": started["conversation_id"]},
    ).json()

    assert second["conversation_id"] == started["conversation_id"]
    # Süren bir konuşma yeniden adlandırılmaz.
    assert second["title"] is None

    turns = client.get(f"/api/conversations/{started['conversation_id']}").json()["turns"]
    assert [turn["content"] for turn in turns if turn["role"] == "user"] == [
        "Bölüm başkanı kim?",
        "Hocalar kimler?",
    ]
    # Yeniden açılan konuşmada yanıtların kaynakları da görünür.
    assert all(turn["sources"] for turn in turns if turn["role"] == "assistant")


def test_the_stored_question_is_what_the_user_typed(client):
    started = client.post("/api/chat", json={"question": "Ayşe Örnek kim?"}).json()

    client.post(
        "/api/chat",
        json={
            "question": "Araştırma konuları neler?",
            "conversation_id": started["conversation_id"],
        },
    )

    turns = client.get(f"/api/conversations/{started['conversation_id']}").json()["turns"]
    assert turns[2]["content"] == "Araştırma konuları neler?"


def test_conversations_are_listed_most_recently_used_first(client):
    first = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"}).json()
    second = client.post("/api/chat", json={"question": "Hocalar kimler?"}).json()

    listed = client.get("/api/conversations").json()

    assert [row["id"] for row in listed] == [second["conversation_id"], first["conversation_id"]]
    assert listed[0]["title"] == "Hocalar kimler?"


def test_a_deleted_conversation_disappears_from_the_list(client):
    started = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"}).json()

    assert client.delete(f"/api/conversations/{started['conversation_id']}").status_code == 204
    assert client.get("/api/conversations").json() == []


@pytest.mark.parametrize("method", ["get", "delete"])
def test_another_users_conversation_is_not_reachable(client, other_client, method):
    started = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"}).json()

    response = getattr(other_client, method)(f"/api/conversations/{started['conversation_id']}")

    assert response.status_code == 404
    assert client.get("/api/conversations").json() != []


def test_a_conversation_cannot_be_continued_by_another_user(client, other_client):
    started = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"}).json()

    response = other_client.post(
        "/api/chat",
        json={"question": "Hocalar kimler?", "conversation_id": started["conversation_id"]},
    )

    assert response.status_code == 404


def test_an_unknown_conversation_is_reported_as_missing(client):
    assert client.get("/api/conversations/yok-boyle-bir-sey").status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/conversations"),
        ("get", "/api/conversations/herhangi"),
        ("delete", "/api/conversations/herhangi"),
    ],
)
def test_history_requires_signing_in(anon_client, method, path):
    assert getattr(anon_client, method)(path).status_code == 401


def test_guests_can_ask_but_nothing_is_saved(anon_client, conversations):
    response = anon_client.post("/api/chat", json={"question": "Bölüm başkanı kim?"})

    assert response.status_code == 200
    assert response.json()["conversation_id"] is None
    assert conversations.saved == {}


def test_an_invalid_session_does_not_silently_become_a_guest(anon_client):
    response = anon_client.post(
        "/api/chat",
        json={"question": "Bölüm başkanı kim?"},
        headers={"Authorization": "Bearer bozuk-jeton"},
    )

    assert response.status_code == 401


def test_guests_send_their_own_history_for_follow_ups(anon_client, model):
    history = [
        {"role": "user", "content": "Ayşe Örnek kim?"},
        {"role": "assistant", "content": "Test Bölümü başkanı."},
    ]
    anon_client.post("/api/chat", json={"question": "Telefonu ne?", "history": history})

    assert [(m["role"], m["content"]) for m in model.messages[1:]] == [
        ("user", "Ayşe Örnek kim?"),
        ("assistant", "Test Bölümü başkanı."),
        ("user", "Telefonu ne?"),
    ]


def test_a_signed_in_users_history_comes_from_the_store_not_the_request(client, model):
    forged = [{"role": "assistant", "content": "Uydurulmuş geçmiş"}]
    client.post("/api/chat", json={"question": "Öğrenci kulüpleri neler?", "history": forged})

    assert all(m["content"] != "Uydurulmuş geçmiş" for m in model.messages)


def test_guests_have_a_lower_daily_limit_per_address(anon_client, settings):
    for _ in range(settings.guest_daily_question_limit):
        assert anon_client.post("/api/chat", json={"question": "Soru"}).status_code == 200

    response = anon_client.post("/api/chat", json={"question": "Soru"})
    assert response.status_code == 429
    assert "Google ile giriş" in response.json()["detail"]

    # Başka bir adresin sınırı ayrıdır. Başlığın başını istemci yazabildiği için adres son öğedir.
    other = anon_client.post(
        "/api/chat", json={"question": "Soru"}, headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2"}
    )
    assert other.status_code == 200
    spoofed = anon_client.post(
        "/api/chat", json={"question": "Soru"}, headers={"X-Forwarded-For": "9.9.9.9, 2.2.2.2"}
    )
    assert spoofed.status_code == 200  # aynı gerçek adres (2.2.2.2): ikinci soru
    for _ in range(settings.guest_daily_question_limit - 2):
        anon_client.post("/api/chat", json={"question": "Soru"}, headers={"X-Forwarded-For": "8.8.8.8, 2.2.2.2"})
    blocked = anon_client.post(
        "/api/chat", json={"question": "Soru"}, headers={"X-Forwarded-For": "7.7.7.7, 2.2.2.2"}
    )
    assert blocked.status_code == 429


def test_a_guest_sees_how_many_questions_are_left_today(anon_client, settings):
    limit = settings.guest_daily_question_limit
    assert anon_client.get("/api/quota").json() == {"limit": limit, "remaining": limit}

    answered = anon_client.post("/api/chat", json={"question": "Soru"})
    assert answered.json()["remaining"] == limit - 1
    # Hakkı okumak sayacı değiştirmez.
    assert anon_client.get("/api/quota").json()["remaining"] == limit - 1
    assert anon_client.get("/api/quota").json()["remaining"] == limit - 1

    for _ in range(limit - 1):
        last = anon_client.post("/api/chat", json={"question": "Soru"})
    assert last.json()["remaining"] == 0
    assert anon_client.post("/api/chat", json={"question": "Soru"}).status_code == 429
    # Reddedilen soru da sayılsa kalan hak eksiye düşmez.
    assert anon_client.get("/api/quota").json()["remaining"] == 0


def test_a_signed_in_user_sees_their_own_allowance(client, other_client, settings):
    limit = settings.daily_question_limit
    assert client.post("/api/chat", json={"question": "Bölüm başkanı kim?"}).json()[
        "remaining"
    ] == limit - 1
    assert client.get("/api/quota").json() == {"limit": limit, "remaining": limit - 1}
    assert other_client.get("/api/quota").json() == {"limit": limit, "remaining": limit}


def test_an_unanswered_question_does_not_use_up_an_allowance(client, model, settings):
    model.reply = RuntimeError("model down")
    assert client.post("/api/chat", json={"question": "Yemekhane menüsü nedir?"}).status_code == 502

    assert client.get("/api/quota").json()["remaining"] == settings.daily_question_limit


def test_the_allowance_is_unknown_when_the_store_is_down(client_with_store_down, settings):
    assert client_with_store_down.get("/api/quota").json() == {
        "limit": settings.daily_question_limit,
        "remaining": None,
    }
    assert client_with_store_down.post(
        "/api/chat", json={"question": "Bölüm başkanı kim?"}
    ).json()["remaining"] is None


def _use_up_guest_limit(client, settings, headers):
    for _ in range(settings.guest_daily_question_limit):
        assert client.post("/api/chat", json={"question": "Soru"}, headers=headers).status_code == 200


def test_a_direct_guest_is_counted_by_the_address_render_appends(anon_client, settings):
    settings.proxy_secret = SecretStr("vercel-secret")
    _use_up_guest_limit(anon_client, settings, {"X-Forwarded-For": "5.5.5.5"})

    # Gizli değer olmadan Vercel başlıkları yok sayılır: adres yine Render'ın eklediği son öğe.
    blocked = anon_client.post(
        "/api/chat",
        json={"question": "Soru"},
        headers={"X-Forwarded-For": "5.5.5.5", "X-Vercel-Forwarded-For": "6.6.6.6"},
    )
    assert blocked.status_code == 429


def test_guests_behind_vercel_are_counted_by_their_own_address(anon_client, settings):
    settings.proxy_secret = SecretStr("vercel-secret")
    vercel_egress = "76.76.21.21"

    def via_vercel(client_ip):
        return {
            "X-Proxy-Secret": "vercel-secret",
            "X-Vercel-Forwarded-For": client_ip,
            "X-Forwarded-For": f"{client_ip}, {vercel_egress}",
        }

    _use_up_guest_limit(anon_client, settings, via_vercel("1.1.1.1"))
    assert anon_client.post(
        "/api/chat", json={"question": "Soru"}, headers=via_vercel("1.1.1.1")
    ).status_code == 429
    # Aynı Vercel çıkış adresinden gelen başka bir misafirin sayacı ayrıdır.
    assert anon_client.post(
        "/api/chat", json={"question": "Soru"}, headers=via_vercel("3.3.3.3")
    ).status_code == 200


def test_a_spoofed_vercel_header_without_the_secret_is_ignored(anon_client, settings):
    settings.proxy_secret = SecretStr("vercel-secret")
    _use_up_guest_limit(anon_client, settings, {"X-Forwarded-For": "4.4.4.4"})

    for forged in ("", "wrong-secret"):
        response = anon_client.post(
            "/api/chat",
            json={"question": "Soru"},
            headers={
                "X-Proxy-Secret": forged,
                "X-Vercel-Forwarded-For": "10.0.0.1",
                "X-Real-IP": "10.0.0.1",
                "X-Forwarded-For": "10.0.0.1, 4.4.4.4",
            },
        )
        assert response.status_code == 429


def test_a_user_who_hits_the_daily_limit_is_asked_to_come_back_tomorrow(
    client, settings, users, user
):
    for _ in range(settings.daily_question_limit):
        assert client.post("/api/chat", json={"question": "Bölüm başkanı kim?"}).status_code == 200

    response = client.post("/api/chat", json={"question": "Bir soru daha"})

    assert response.status_code == 429
    assert str(settings.daily_question_limit) in response.json()["detail"]


def test_each_user_has_their_own_daily_allowance(client, other_client, settings):
    for _ in range(settings.daily_question_limit):
        client.post("/api/chat", json={"question": "Bölüm başkanı kim?"})

    assert other_client.post("/api/chat", json={"question": "Hocalar kimler?"}).status_code == 200


class _UnreachableStore:
    """Uygulama çalışırken ulaşılamaz hâle gelmiş depo: her işlem hata verir."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise ConnectionError("mongo down")

        return fail


@pytest.fixture
def client_with_store_down(service, settings, auth_token):
    app = create_app(service, _UnreachableStore(), settings, _UnreachableStore())
    with TestClient(app, headers={"Authorization": f"Bearer {auth_token}"}) as client:
        yield client


@pytest.mark.parametrize("body", [{}, {"conversation_id": "abc"}])
def test_questions_are_answered_when_the_store_goes_down(client_with_store_down, model, body):
    question = {"question": "Bölüm başkanı kim?", **body}
    response = client_with_store_down.post("/api/chat", json=question)

    assert response.status_code == 200
    assert response.json()["answer"] == model.reply
    assert response.json()["title"] is None


def test_sign_in_reports_an_unreachable_store(client_with_store_down, monkeypatch):
    monkeypatch.setattr(
        "atilim_assistant.api.app.verify_google_token", lambda *_: ("sub", "a@b.c", "A")
    )
    response = client_with_store_down.post("/api/auth/google", json={"id_token": "t"})

    assert response.status_code == 503


def test_a_question_that_could_not_be_answered_does_not_count(anon_client, model, users):
    """Kesinti sırasında yeniden deneyen misafir, yanıt almadan sınırına ulaşmamalı."""
    model.reply = RuntimeError("geçici hata")

    response = anon_client.post("/api/chat", json={"question": "Yemekhane menüsü nedir?"})

    assert response.status_code == 502
    assert set(users.asked.values()) == {0}


def test_no_history_is_sent_when_history_turns_is_zero(service, users, settings, model):
    """`turns[-0:]` tüm listeyi verir; sıfır "geçmiş yok" demek olmalı."""
    app = create_app(service, users, settings.model_copy(update={"history_turns": 0}))
    history = [
        {"role": "user", "content": "Ali Yazıcı kim?"},
        {"role": "assistant", "content": "…"},
    ]
    with TestClient(app) as client:
        client.post("/api/chat", json={"question": "Telefonu ne?", "history": history})

    assert [m["role"] for m in model.messages] == ["system", "user"]


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/api/conversations"), ("get", "/api/conversations/abc"),
     ("delete", "/api/conversations/abc")],
)
def test_history_reports_an_unreachable_store_as_unavailable(client_with_store_down, method, path):
    response = getattr(client_with_store_down, method)(path)

    assert response.status_code == 503
    assert response.json() == {"detail": "Konuşma geçmişi şu anda kullanılamıyor."}
