from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from atilim_assistant.api.app import UNAVAILABLE_DETAIL, create_app
from atilim_assistant.chat import service as chat_service
from atilim_assistant.chat.service import ChatService
from atilim_assistant.chat.tools import Tools
from atilim_assistant.domain import Completion, Turn
from atilim_assistant.retrieval.catalog import Catalog
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher
from tests.conftest import FakeRetriever, tool_call


def _course(code: str, name: str) -> dict:
    return {
        "code": code, "name": name, "category": "Zorunlu Dersler", "theory": 4, "practice": 0,
        "lab": 0, "credit": 4.0, "akts": 6.0, "precondition": "", "content": "",
    }


@pytest.fixture
def history() -> list[Turn]:
    return [
        Turn(role="user", content="Ayşe Örnek kim?"),
        Turn(role="assistant", content="Prof. Dr. Ayşe ÖRNEK, Test Bölümü başkanıdır."),
    ]


def test_model_answers_from_tool_results_and_cites_each_page_once(service, model, staff_source):
    model.script = [tool_call("belge_ara", sorgu="öğrenci kulüpleri")]

    answer = service.answer("Öğrenci kulüpleri neler?")

    tool_message = next(m for m in model.messages if m["role"] == "tool")
    assert "Görev: Bölüm Başkanı" in tool_message["content"]
    assert answer.text == model.reply
    assert [(c.title, c.url) for c in answer.citations] == [(staff_source.title, staff_source.url)]


def test_model_answers_are_not_marked_as_prepared(service):
    assert service.answer("Öğrenci kulüpleri neler?").prepared is False


def test_the_model_answers_before_prepared_answers_are_tried(service, model):
    # "Hocalar kimler?" bir hazır yanıta uyar; model çalışırken yine de model yanıtlar.
    answer = service.answer("Hocalar kimler?")

    assert answer.prepared is False
    assert model.calls == 1


def test_the_model_sees_the_conversation_history(service, model, history):
    service.answer("Araştırma konuları neler?", history)

    assert [(m["role"], m["content"]) for m in model.messages[1:]] == [
        ("user", "Ayşe Örnek kim?"),
        ("assistant", "Prof. Dr. Ayşe ÖRNEK, Test Bölümü başkanıdır."),
        ("user", "Araştırma konuları neler?"),
    ]


def test_tool_rounds_are_capped_and_the_last_round_must_answer(service, model):
    model.script = [tool_call("belge_ara", sorgu="x") for _ in range(10)]
    model.script.insert(4, Completion(content="Son turda yanıt."))

    assert service.answer("Döngüye giren soru").text == "Son turda yanıt."
    assert model.calls == 5
    assert model.tools == []


def test_misspelled_course_codes_are_corrected_before_the_model_sees_them(model, staff_answers):
    catalog = replace(Catalog.empty(), courses=[_course("MATH276", "Diferansiyel Denklemler")])
    service = ChatService(Tools(catalog, FakeRetriever([])), model, PreparedAnswerMatcher(staff_answers))

    service.answer("MATF276 nedir?")

    assert model.messages[-1] == {"role": "user", "content": "MATH276 nedir?"}


def test_during_a_cooldown_follow_ups_get_prepared_answers_without_the_model(
    service, model, history
):
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")
    with pytest.raises(RuntimeError):
        service.answer("Öğrenci kulüpleri neler?")
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
    with pytest.raises(RuntimeError):
        service.answer("Öğrenci kulüpleri neler?")  # soğumayı tetikler
    model.reply = "Model yeniden yanıt veriyor."

    # Soğuma süresince hazır yanıt her zaman öncelikli (model çağrılmaz).
    assert service.answer("Hocalar kimler?").prepared is True
    assert model.calls == 1

    # Soğuma bittikten sonra hazır yanıtı olmayan soru modele gider.
    now += 61
    assert service.answer("Öğrenci kulüpleri neler?").text == "Model yeniden yanıt veriyor."
    assert model.calls == 2


def test_exhausted_quota_waits_longer_than_a_transient_failure(service, model, monkeypatch):
    now = 1000.0
    monkeypatch.setattr(chat_service.time, "monotonic", lambda: now)
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")
    with pytest.raises(RuntimeError):
        service.answer("Öğrenci kulüpleri neler?")  # kota hatasını tetikler (uzun soğuma)
    model.reply = "Model yeniden yanıt veriyor."

    # 61 saniye sonra geçici soğuma biterdi; kota soğuması devam ediyor.
    # Hazır yanıtı olan soru yine de doğrudan döner.
    now += 61
    assert service.answer("Hocalar kimler?").prepared is True
    assert model.calls == 1

    # Kota soğuması sürerken hazır yanıtı olmayan soru modele hiç gönderilmez.
    with pytest.raises(RuntimeError, match="kota"):
        service.answer("Öğrenci kulüpleri neler?")
    assert model.calls == 1

    # Kota soğuması bittikten sonra hazır yanıtı olmayan soru modele gider.
    now += 3600
    assert service.answer("Öğrenci kulüpleri neler?").text == "Model yeniden yanıt veriyor."


def test_model_is_still_tried_during_cooldown_when_no_prepared_answer_exists(service, model):
    model.reply = RuntimeError("geçici hata")
    service.answer("Bölüm başkanı kim?")
    model.reply = "Bu bilgi elimdeki verilerde yok."

    answer = service.answer("Yemekhane menüsü nedir?")
    assert answer.text == "Bu bilgi elimdeki verilerde yok."
    # Model bağlamı yetersiz bulduğunda getirilen sayfalar kaynak olarak gösterilmez.
    assert answer.citations == []


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "auth_required": True}


def test_without_sign_in_configured_questions_are_answered_as_guest(service, settings):
    guest_settings = settings.model_copy(update={"google_client_id": ""})
    with TestClient(create_app(service, settings=guest_settings)) as guest:
        assert guest.get("/api/health").json()["auth_required"] is False
        response = guest.post("/api/chat", json={"question": "Öğrenci kulüpleri neler?"})

    assert response.status_code == 200
    assert response.json()["conversation_id"] is None


def test_chat_returns_answer_with_sources(client, model, staff_source):
    # Model belge aracını çağırır; aracın getirdiği sayfa yanıtın kaynağı olur.
    model.script = [tool_call("belge_ara", sorgu="öğrenci kulüpleri")]
    response = client.post("/api/chat", json={"question": "  Öğrenci kulüpleri neler?  "})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Bölüm başkanı Prof. Dr. Ayşe ÖRNEK'tir."
    assert body["sources"] == [{"title": staff_source.title, "url": staff_source.url}]
    assert body["prepared"] is False


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
