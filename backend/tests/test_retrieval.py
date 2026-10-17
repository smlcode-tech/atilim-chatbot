import pytest

from atilim_assistant.domain import Document, SourceContent
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
    store = DocumentStore(tmp_path / "chroma", "test", "fake-model")
    index_content(staff_source, staff_content, embedder, store, prepared_store)
    return store


def test_store_round_trips_documents(store, staff_documents):
    assert sorted(store.all(), key=lambda d: d.id) == sorted(staff_documents, key=lambda d: d.id)


def test_store_refuses_index_built_with_another_embed_model(store, tmp_path):
    with pytest.raises(RuntimeError, match="fake-model"):
        DocumentStore(tmp_path / "chroma", "test", "other-model")


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
    # "Oyun" vektör aramasında, "Ayşe Örnek" anahtar kelime aramasında birinci gelir. Sahte
    # embedder diğer belgelere aynı vektörü verdiği için kalan sıra belirsizdir; yalnızca
    # iki aramanın birincilerinin sonuçta yer aldığı doğrulanır.
    retriever = HybridRetriever(store, embedder, top_k=3, max_chars=100_000)
    titles = {document.title for document in retriever.retrieve("Oyun mu, Ayşe Örnek mi?")}
    assert {"Öğr. Gör. Mehmet DENEME", "Prof. Dr. Ayşe ÖRNEK"} <= titles


def test_hybrid_retriever_skips_documents_that_overflow_the_context_budget(
    store, embedder, staff_documents
):
    budget = min(len(document.text) for document in staff_documents)
    retriever = HybridRetriever(store, embedder, top_k=3, max_chars=budget)
    results = retriever.retrieve("Oyun mu, Ayşe Örnek mi?")
    assert sum(len(document.text) for document in results) <= budget


_META = {"source_id": "s", "source_title": "s", "url": "", "unit": "", "category": ""}


def test_lexical_search_ignores_filler_words():
    # "nasıl" içerik taşımaz; sayılsaydı yalnızca onu paylaşan belge staj belgesinin önüne geçerdi.
    documents = [
        Document(id="1", title="Ortak eğitim nasıl notlandırılır?", text="Nasıl? Nasıl?", **_META),
        Document(id="2", title="Yaz Stajı Genel Bilgi", text="Yaz stajı uzun açıklama", **_META),
    ]
    assert [d.id for d in LexicalIndex(documents).search("Yaz stajı nasıl yapılır?", 5)] == ["2"]


@pytest.mark.parametrize("query", ["SE212 ön koşulu", "SE 212 ön koşulu"])
def test_lexical_search_matches_course_codes_with_or_without_space(query):
    documents = [
        Document(id="1", title="SE212 Ön Koşulu", text="SE212 için ön koşul yok", **_META),
        Document(id="2", title="CMPE325 Ön Koşulu", text="Ön koşul: CMPE 225", **_META),
    ]
    assert LexicalIndex(documents).search(query, 1)[0].id == "1"
