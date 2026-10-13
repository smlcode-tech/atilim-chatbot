import pytest

from atilim_assistant.api.app import UNAVAILABLE_DETAIL
from atilim_assistant.chat import service as chat_service
from atilim_assistant.domain import Turn


@pytest.fixture
def history() -> list[Turn]:
    return [
        Turn(role="user", content="Ayşe Örnek kim?"),
        Turn(role="assistant", content="Prof. Dr. Ayşe ÖRNEK, Test Bölümü başkanıdır."),
    ]


def test_answer_grounds_the_model_and_cites_each_page_once(service, model, staff_source):
    # Hazır yanıtı olmayan soru LLM yoluna gider; belge bağlamı prompt'ta yer alır.
    answer = service.answer("Öğrenci kulüpleri neler?")

    assert "Görev: Bölüm Başkanı" in model.prompt
    assert model.prompt.endswith("SORU: Öğrenci kulüpleri neler?")
    assert [(c.title, c.url) for c in answer.citations] == [(staff_source.title, staff_source.url)]


def test_model_answers_are_not_marked_as_prepared(service):
    assert service.answer("Öğrenci kulüpleri neler?").prepared is False


def test_follow_up_questions_are_rewritten_before_retrieval(service, model, history):
    # Model yeniden yazma çağrısı yapılır (1 çağrı); yeniden yazılan soru hazır yanıtla
    # eşleştiği için LLM'e ikinci bir çağrı gitmez.
    model.reply = "Prof. Dr. Ayşe ÖRNEK'in araştırma konuları neler?"

    answer = service.answer("Araştırma konuları neler?", history)

    assert model.calls == 1
    assert answer.prepared is True


def test_self_contained_questions_spare_the_contextualization_call(service, model, history):
    service.answer("Blok zinciri ile ilgilenen öğretim üyeleri kimler?", history)

    assert model.calls == 1
    assert model.prompt.endswith("SORU: Blok zinciri ile ilgilenen öğretim üyeleri kimler?")


def test_a_dead_model_is_not_asked_to_rewrite(service, model, history):
    # Hazır yanıtı olmayan soru modeli çağırır ve çöktürür; soğuma süresi başlar.
    model.reply = RuntimeError("429 RESOURCE_EXHAUSTED")
    with pytest.raises(RuntimeError):
        service.answer("Öğrenci kulüpleri neler?")
    calls_after_failure = model.calls

    # Soğuma sırasında takip sorusu yeniden yazılmaz; hazır yanıt döner.
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

    # Kota soğuması bittikten sonra hazır yanıtı olmayan soru modele gider.
    now += 3600
    assert service.answer("Öğrenci kulüpleri neler?").text == "Model yeniden yanıt veriyor."


def test_model_is_still_tried_during_cooldown_when_no_prepared_answer_exists(service, model):
    model.reply = RuntimeError("geçici hata")
    service.answer("Bölüm başkanı kim?")
    model.reply = "Bu bilgi elimdeki verilerde yok."

    assert service.answer("Yemekhane menüsü nedir?").text == "Bu bilgi elimdeki verilerde yok."


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_returns_answer_with_sources(client, staff_source):
    # Hazır yanıtı olmayan soru LLM'e gider; kaynaklarla birlikte döner.
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
