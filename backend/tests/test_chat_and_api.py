import pytest
from fastapi.testclient import TestClient

from atilim_assistant.api.app import create_app
from atilim_assistant.chat.service import ChatService


class FakeRetriever:
    def __init__(self, documents):
        self._documents = documents

    def retrieve(self, query):
        return self._documents


class FakeModel:
    def __init__(self, reply="Bölüm başkanı Prof. Dr. Ayşe ÖRNEK'tir."):
        self.reply = reply
        self.prompt = None

    def generate(self, system, prompt):
        self.prompt = prompt
        return self.reply


@pytest.fixture
def model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def service(staff_documents, model) -> ChatService:
    return ChatService(FakeRetriever(staff_documents), model)


@pytest.fixture
def client(service):
    with TestClient(create_app(service)) as client:
        yield client


def test_answer_grounds_the_model_and_cites_each_page_once(service, model, staff_source):
    answer = service.answer("Bölüm başkanı kim?")

    assert "Görev: Bölüm Başkanı" in model.prompt
    assert model.prompt.endswith("SORU: Bölüm başkanı kim?")
    assert [(c.title, c.url) for c in answer.citations] == [(staff_source.title, staff_source.url)]


def test_empty_model_reply_is_an_error(staff_documents):
    service = ChatService(FakeRetriever(staff_documents), FakeModel(reply="  "))
    with pytest.raises(RuntimeError):
        service.answer("Bölüm başkanı kim?")


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_returns_answer_with_sources(client, staff_source):
    response = client.post("/api/chat", json={"question": "  Bölüm başkanı kim?  "})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Bölüm başkanı Prof. Dr. Ayşe ÖRNEK'tir.",
        "sources": [{"title": staff_source.title, "url": staff_source.url}],
    }


@pytest.mark.parametrize("body", [{}, {"question": "   "}, {"question": "a" * 1001}])
def test_chat_rejects_invalid_questions(client, body):
    response = client.post("/api/chat", json=body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_chat_reports_generation_failures(staff_documents):
    failing = ChatService(FakeRetriever(staff_documents), FakeModel(reply=""))
    with TestClient(create_app(failing)) as client:
        response = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Yanıt oluşturulurken bir hata oluştu."}
