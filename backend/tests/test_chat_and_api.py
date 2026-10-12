import pytest
from fastapi.testclient import TestClient

from atilim_assistant.api.app import UNAVAILABLE_DETAIL, create_app
from atilim_assistant.chat import service as chat_service
from atilim_assistant.chat.service import ChatService
from atilim_assistant.domain import Turn
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher


class FakeRetriever:
    def __init__(self, documents):
        self._documents = documents

    def retrieve(self, query):
        return self._documents


class FakeModel:
    def __init__(self, reply="Bölüm başkanı Prof. Dr. Ayşe ÖRNEK'tir."):
        self.reply = reply
        self.prompt = None
        self.calls = 0

    def generate(self, system, prompt):
        self.calls += 1
        self.prompt = prompt
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture
def model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def service(staff_documents, staff_answers, model) -> ChatService:
    return ChatService(FakeRetriever(staff_documents), model, PreparedAnswerMatcher(staff_answers))


@pytest.fixture
def history() -> list[Turn]:
    return [
        Turn(role="user", content="Ayşe Örnek kim?"),
        Turn(role="assistant", content="Prof. Dr. Ayşe ÖRNEK, Test Bölümü başkanıdır."),
    ]


@pytest.fixture
def client(service):
    with TestClient(create_app(service)) as client:
        yield client


def test_answer_grounds_the_model_and_cites_each_page_once(service, model, staff_source):
    answer = service.answer("Bölüm başkanı kim?")

    assert "Görev: Bölüm Başkanı" in model.prompt
    assert model.prompt.endswith("SORU: Bölüm başkanı kim?")
    assert [(c.title, c.url) for c in answer.citations] == [(staff_source.title, staff_source.url)]


def test_model_answers_are_not_marked_as_prepared(service):
    assert service.answer("Bölüm başkanı kim?").prepared is False


def test_follow_up_questions_are_rewritten_before_retrieval(service, model, history):
    model.reply = "Prof. Dr. Ayşe ÖRNEK'in araştırma konuları neler?"

    service.answer("Araştırma konuları neler?", history)

    assert model.calls == 2
    assert model.prompt.endswith("SORU: Prof. Dr. Ayşe ÖRNEK'in araştırma konuları neler?")


def test_self_contained_questions_spare_the_contextualization_call(service, model, history):
    service.answer("Blok zinciri ile ilgilenen öğretim üyeleri kimler?", history)

    assert model.calls == 1
    assert model.prompt.endswith("SORU: Blok zinciri ile ilgilenen öğretim üyeleri kimler?")


def test_a_dead_model_is_not_asked_to_rewrite(service, model, history):
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")
    service.answer("Bölüm başkanı kim?")
    calls_after_failure = model.calls

    assert service.answer("Araştırma konuları neler?", history).prepared is True
    assert model.calls == calls_after_failure


@pytest.mark.parametrize("reply", [RuntimeError("429 RESOURCE_EXHAUSTED"), "  "])
def test_prepared_answer_is_given_when_the_model_fails(service, model, staff_source, reply):
    model.reply = reply

    answer = service.answer("Bölüm başkanı kim?")

    assert answer.text == "Test Bölümü görevlileri:\n- Prof. Dr. Ayşe ÖRNEK (Bölüm Başkanı)"
    assert answer.prepared is True
    assert [(c.title, c.url) for c in answer.citations] == [(staff_source.title, staff_source.url)]


def test_model_failure_is_raised_when_no_prepared_answer_covers_the_question(service, model):
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")
    with pytest.raises(RuntimeError, match="429"):
        service.answer("Yemekhane menüsü nedir?")


def test_failed_model_is_skipped_until_the_cooldown_ends(service, model, monkeypatch):
    now = 1000.0
    monkeypatch.setattr(chat_service.time, "monotonic", lambda: now)
    model.reply = RuntimeError("geçici hata")
    service.answer("Bölüm başkanı kim?")
    model.reply = "Model yeniden yanıt veriyor."

    assert service.answer("Hocalar kimler?").prepared is True
    assert model.calls == 1

    now += 61
    assert service.answer("Hocalar kimler?").text == "Model yeniden yanıt veriyor."
    assert model.calls == 2


def test_exhausted_quota_waits_longer_than_a_transient_failure(service, model, monkeypatch):
    now = 1000.0
    monkeypatch.setattr(chat_service.time, "monotonic", lambda: now)
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")
    service.answer("Bölüm başkanı kim?")
    model.reply = "Model yeniden yanıt veriyor."

    now += 61
    assert service.answer("Hocalar kimler?").prepared is True
    assert model.calls == 1

    now += 3600
    assert service.answer("Hocalar kimler?").text == "Model yeniden yanıt veriyor."


def test_model_is_still_tried_during_cooldown_when_no_prepared_answer_exists(service, model):
    model.reply = RuntimeError("geçici hata")
    service.answer("Bölüm başkanı kim?")
    model.reply = "Bu bilgi elimdeki verilerde yok."

    assert service.answer("Yemekhane menüsü nedir?").text == "Bu bilgi elimdeki verilerde yok."


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_returns_answer_with_sources(client, staff_source):
    response = client.post("/api/chat", json={"question": "  Bölüm başkanı kim?  "})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Bölüm başkanı Prof. Dr. Ayşe ÖRNEK'tir.",
        "sources": [{"title": staff_source.title, "url": staff_source.url}],
        "prepared": False,
    }


def test_chat_marks_prepared_answers(client, model):
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")

    response = client.post("/api/chat", json={"question": "Bölüm başkanı kim?"})

    assert response.status_code == 200
    assert response.json()["prepared"] is True
    assert response.json()["answer"].startswith("Test Bölümü görevlileri")


@pytest.mark.parametrize("body", [{}, {"question": "   "}, {"question": "a" * 1001}])
def test_chat_rejects_invalid_questions(client, body):
    response = client.post("/api/chat", json=body)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_chat_reports_questions_that_cannot_be_answered(client, model):
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")

    response = client.post("/api/chat", json={"question": "Yemekhane menüsü nedir?"})

    assert response.status_code == 502
    assert response.json() == {"detail": UNAVAILABLE_DETAIL}
