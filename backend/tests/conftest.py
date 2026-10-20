import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from atilim_assistant.api.app import create_app
from atilim_assistant.auth import issue_token
from atilim_assistant.chat.service import ChatService
from atilim_assistant.chat.tools import Tools
from atilim_assistant.config import Settings
from atilim_assistant.domain import (
    Completion,
    ConversationSummary,
    Document,
    PreparedAnswer,
    Source,
    SourceContent,
    ToolCall,
    Turn,
    User,
)
from atilim_assistant.ingestion.parsers.departments.software_engineering import (
    academic_staff,
    ders_programi,
)
from atilim_assistant.retrieval.catalog import Catalog
from atilim_assistant.retrieval.prepared import PreparedAnswerMatcher

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def no_timetable(monkeypatch):
    """Ayrıştırıcılar ders programını ağdan çeker; testler programı açıkça verir."""
    monkeypatch.setattr(ders_programi, "current", lambda: None)


@pytest.fixture
def staff_source() -> Source:
    return Source(
        id="test-akademik-personel",
        title="Test Bölümü — Akademik Personel",
        url="https://example.edu/akademik-personel",
        unit="Test Bölümü",
        category="akademik-personel",
        parser=academic_staff.parse,
    )


@pytest.fixture
def staff_content(staff_source: Source) -> SourceContent:
    html = (FIXTURES / "academic_staff.html").read_text(encoding="utf-8")
    return academic_staff.parse(html, staff_source)


@pytest.fixture
def staff_documents(staff_content: SourceContent) -> list[Document]:
    return staff_content.documents


@pytest.fixture
def staff_answers(staff_content: SourceContent) -> list[PreparedAnswer]:
    return staff_content.prepared_answers


class FakeEmbedder:
    """Metni, içinde geçen anahtar kelimelere göre iki boyutlu bir vektöre çevirir."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0] if "Oyun" in text else [0.0, 1.0]


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


class InMemoryUserRepository:
    """`UserRepository` portunun test karşılığı: Google kimliği başına tek kullanıcı."""

    def __init__(self) -> None:
        self.saved: dict[str, User] = {}
        self.asked: dict[tuple[str, str], int] = {}

    def upsert(self, google_sub: str, email: str, name: str) -> str:
        self.saved[google_sub] = User(id=google_sub, email=email, name=name)
        return google_sub

    def count_question(self, user_id: str, day: str) -> int:
        self.asked[user_id, day] = self.asked.get((user_id, day), 0) + 1
        return self.asked[user_id, day]

    def count_guest_question(self, guest_key: str, day: str) -> int:
        return self.count_question(f"misafir:{guest_key}", day)

    def uncount_question(self, user_id: str, day: str) -> None:
        if self.asked.get((user_id, day), 0) > 0:
            self.asked[user_id, day] -= 1

    def uncount_guest_question(self, guest_key: str, day: str) -> None:
        self.uncount_question(f"misafir:{guest_key}", day)


class InMemoryConversationRepository:
    """`ConversationRepository` portunun test karşılığı.

    Sahiplik kontrolü gerçek depodaki gibi sorgunun parçasıdır: başkasının konuşması
    "yok" sayılır, "yasak" değil.
    """

    def __init__(self) -> None:
        self.saved: dict[str, dict] = {}
        self._next = 0

    def start(self, user_id: str, title: str) -> str:
        self._next += 1
        conversation_id = f"conversation-{self._next}"
        self.saved[conversation_id] = {
            "user_id": user_id,
            "title": title,
            "turns": [],
            "updated_at": datetime.now(UTC),
        }
        return conversation_id

    def add_turns(self, conversation_id: str, user_id: str, turns: list[Turn]) -> None:
        conversation = self._owned(conversation_id, user_id)
        if conversation is None:
            return
        conversation["turns"].extend(turns)
        conversation["updated_at"] = datetime.now(UTC)

    def turns(self, conversation_id: str, user_id: str) -> list[Turn] | None:
        conversation = self._owned(conversation_id, user_id)
        return None if conversation is None else list(conversation["turns"])

    def list_for(self, user_id: str) -> list[ConversationSummary]:
        owned = [
            ConversationSummary(id=key, title=value["title"], updated_at=value["updated_at"])
            for key, value in self.saved.items()
            if value["user_id"] == user_id
        ]
        return sorted(owned, key=lambda summary: summary.updated_at, reverse=True)

    def delete(self, conversation_id: str, user_id: str) -> bool:
        if self._owned(conversation_id, user_id) is None:
            return False
        del self.saved[conversation_id]
        return True

    def _owned(self, conversation_id: str, user_id: str) -> dict | None:
        conversation = self.saved.get(conversation_id)
        if conversation is None or conversation["user_id"] != user_id:
            return None
        return conversation


@pytest.fixture
def users() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def conversations() -> InMemoryConversationRepository:
    return InMemoryConversationRepository()


@pytest.fixture
def settings() -> Settings:
    """Gerçek ayarlar `.env` ve bir Gemini anahtarı ister; testler kendi ayarlarını kurar."""
    return Settings(
        voyage_api_key=SecretStr("test-voyage-key"),
        groq_api_key=SecretStr("test-groq-key"),
        jwt_secret=SecretStr("test-secret-at-least-32-bytes-long!"),
        google_client_id="test-client-id",
    )


@pytest.fixture
def user() -> User:
    return User(id="google-sub-1", email="ogrenci@atilim.edu.tr", name="Test Öğrenci")


@pytest.fixture
def auth_token(user: User, settings: Settings) -> str:
    return issue_token(user, settings.jwt_secret.get_secret_value(), settings.jwt_ttl_hours)


class FakeRetriever:
    def __init__(self, documents, similar=()):
        self._documents = documents
        self._similar = list(similar)
        self.course_codes = frozenset()

    def retrieve(self, query):
        return self._documents

    def similar_questions(self, query, limit):
        return self._similar[:limit]


class FakeModel:
    """`script` sırayla döndürülecek turlardır (ör. araç çağrıları); tükenince `reply` metni
    döner. `reply` bir istisna ise çağrıda fırlatılır; böylece kesinti davranışı sınanabilir."""

    def __init__(self, reply="Bölüm başkanı Prof. Dr. Ayşe ÖRNEK'tir."):
        self.reply = reply
        self.script: list[Completion] = []
        self.messages: list[dict] = []
        self.tools: list[dict] = []
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        self.messages = [dict(message) for message in messages]
        self.tools = tools
        if isinstance(self.reply, Exception):
            raise self.reply
        if self.script:
            return self.script.pop(0)
        return Completion(content=self.reply)


def tool_call(name: str, **arguments: str) -> Completion:
    """Modelin tek bir araç çağırdığı tur."""
    return Completion(content="", tool_calls=[ToolCall("c1", name, json.dumps(arguments))])


@pytest.fixture
def model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def service(staff_documents, staff_answers, model) -> ChatService:
    tools = Tools(Catalog.empty(), FakeRetriever(staff_documents))
    return ChatService(tools, model, PreparedAnswerMatcher(staff_answers))


@pytest.fixture
def client(service, users, settings, conversations, auth_token):
    app = create_app(service, users, settings, conversations)
    with TestClient(app, headers={"Authorization": f"Bearer {auth_token}"}) as client:
        yield client


@pytest.fixture
def anon_client(service, users, settings, conversations):
    with TestClient(create_app(service, users, settings, conversations)) as client:
        yield client
