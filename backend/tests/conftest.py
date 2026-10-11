from pathlib import Path

import pytest

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.ingestion.parsers import academic_staff

FIXTURES = Path(__file__).parent / "fixtures"


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
