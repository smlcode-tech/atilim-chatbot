import pytest
from fastapi.testclient import TestClient

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


def test_asking_requires_signing_in(anon_client, conversations):
    response = anon_client.post("/api/chat", json={"question": "Bölüm başkanı kim?"})

    assert response.status_code == 401
    assert conversations.saved == {}


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
