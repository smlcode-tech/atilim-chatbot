import pytest

from atilim_assistant.domain import SourceContent
from atilim_assistant.ingestion.pipeline import index_content
from atilim_assistant.retrieval.lexical import LexicalIndex
from atilim_assistant.retrieval.prepared import PreparedAnswerStore
from atilim_assistant.retrieval.retriever import HybridRetriever
from atilim_assistant.retrieval.store import DocumentStore


@pytest.fixture
def prepared_store(tmp_path) -> PreparedAnswerStore:
    return PreparedAnswerStore(tmp_path / "prepared_answers.json")


@pytest.fixture
def store(tmp_path, staff_source, staff_content, embedder, prepared_store) -> DocumentStore:
    store = DocumentStore(tmp_path / "chroma", "test")
    index_content(staff_source, staff_content, embedder, store, prepared_store)
    return store


def test_store_round_trips_documents(store, staff_documents):
    assert sorted(store.all(), key=lambda d: d.id) == sorted(staff_documents, key=lambda d: d.id)


def test_reindexing_a_source_replaces_its_content(
    store, prepared_store, staff_source, staff_content, embedder
):
    assert prepared_store.all() == staff_content.prepared_answers

    smaller = SourceContent(staff_content.documents[:2], staff_content.prepared_answers[:3])
    index_content(staff_source, smaller, embedder, store, prepared_store)

    assert {document.id for document in store.all()} == {d.id for d in smaller.documents}
    assert prepared_store.all() == smaller.prepared_answers


def test_lexical_search_matches_names_despite_suffixes_and_casing(staff_documents):
    results = LexicalIndex(staff_documents).search("ışıl çalışkan'ın telefonu", limit=1)
    assert results[0].title == "Arş. Gör. Işıl ÇALIŞKAN"


def test_lexical_search_returns_nothing_without_common_terms(staff_documents):
    assert LexicalIndex(staff_documents).search("yemekhane menüsü", limit=5) == []


def test_hybrid_retriever_merges_semantic_and_lexical_results(store, embedder):
    # "Oyun" yalnızca vektör aramasında, "Ayşe Örnek" yalnızca anahtar kelime aramasında öne çıkar.
    retriever = HybridRetriever(store, embedder, top_k=2)
    titles = {document.title for document in retriever.retrieve("Oyun mu, Ayşe Örnek mi?")}
    assert titles == {"Öğr. Gör. Mehmet DENEME", "Prof. Dr. Ayşe ÖRNEK"}
