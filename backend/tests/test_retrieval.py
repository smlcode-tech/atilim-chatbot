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
def questions(tmp_path) -> DocumentStore:
    return DocumentStore(tmp_path / "chroma", "test_questions", "fake-model")


@pytest.fixture
def store(
    tmp_path, staff_source, staff_content, embedder, prepared_store, questions
) -> DocumentStore:
    store = DocumentStore(tmp_path / "chroma", "test", "fake-model")
    index_content(staff_source, staff_content, embedder, store, prepared_store, questions)
    return store


def test_store_round_trips_documents(store, staff_documents):
    assert sorted(store.all(), key=lambda d: d.id) == sorted(staff_documents, key=lambda d: d.id)


def test_store_refuses_index_built_with_another_embed_model(store, tmp_path):
    with pytest.raises(RuntimeError, match="fake-model"):
        DocumentStore(tmp_path / "chroma", "test", "other-model")


def test_reindexing_a_source_replaces_its_content(
    store, prepared_store, questions, staff_source, staff_content, embedder
):
    assert prepared_store.all() == staff_content.prepared_answers

    smaller = SourceContent(staff_content.documents[:2], staff_content.prepared_answers[:3])
    index_content(staff_source, smaller, embedder, store, prepared_store, questions)

    assert {document.id for document in store.all()} == {d.id for d in smaller.documents}
    assert prepared_store.all() == smaller.prepared_answers
    assert {d.text for d in questions.all()} == {a.answer for a in smaller.prepared_answers}


def test_every_question_pattern_is_indexed_with_its_answer(store, questions, staff_answers):
    indexed = {(d.title, d.text) for d in questions.all()}
    assert indexed == {(q, a.answer) for a in staff_answers for q in a.questions}


class SpreadEmbedder:
    """"Oyun" geçen metinleri bir yöne, diğerlerini öbür yöne koyar. Ortak `FakeEmbedder`'dan
    farkı, aynı yöndeki metinleri hafifçe ayırmasıdır: yüzlerce özdeş vektörde Chroma'nın
    yaklaşık en yakın komşu araması en yakın olanı kaçırabilir."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        spread = (len(text) % 17) / 100
        return [1.0, spread] if "Oyun" in text else [spread, 1.0]


def test_question_patterns_bring_prepared_answers_into_the_context(
    tmp_path, staff_source, staff_content, prepared_store
):
    # Sorunun sözcükleri hiçbir kalıpla örtüşmese de anlamca yakın kalıbın yanıtı bağlama girer.
    embedder = SpreadEmbedder()
    store = DocumentStore(tmp_path / "spread", "test", "spread")
    questions = DocumentStore(tmp_path / "spread", "test_questions", "spread")
    index_content(staff_source, staff_content, embedder, store, prepared_store, questions)

    retriever = HybridRetriever(store, embedder, top_k=3, max_chars=100_000, questions=questions)
    texts = [document.text for document in retriever.retrieve("Oyun geliştirmeyle uğraşan var mı?")]
    assert any("araştırma konuları arasında" in text for text in texts)


class TopicEmbedder:
    """Metni geçtiği konunun ekseninde birim vektöre çevirir; konusuz metin kendi ekseninde."""

    TOPICS = ("staj", "akts", "başkan")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        axis = next((i for i, t in enumerate(self.TOPICS) if t in text.lower()), len(self.TOPICS))
        return [1.0 if i == axis else 0.0 for i in range(len(self.TOPICS) + 1)]


@pytest.fixture
def pattern_retriever(tmp_path) -> HybridRetriever:
    patterns = [
        ("Yaz stajı kaç gün?", "20 iş günü"),
        ("Staj zorunlu mu?", "Evet"),
        ("Staj sigortası nasıl yapılır?", "SGK"),
        ("Staj sigortası için hangi belgeler gerekli?", "SGK"),  # aynı yanıt
        ("MECE322 kaç AKTS?", "6 AKTS"),
        ("ENG201 kaç AKTS?", "4 AKTS"),  # aynı biçim
        ("Bölüm başkanı kim?", "Ali Yazıcı"),
    ]
    embedder = TopicEmbedder()
    questions = DocumentStore(tmp_path / "patterns", "test_questions", "topic")
    documents = [
        Document(id=str(i), title=title, text=answer, **_META)
        for i, (title, answer) in enumerate(patterns)
    ]
    questions.replace_source("s", documents, embedder.embed_documents([d.title for d in documents]))
    store = DocumentStore(tmp_path / "patterns", "test", "topic")
    return HybridRetriever(store, embedder, top_k=3, max_chars=100_000, questions=questions)


def test_similar_questions_offer_one_pattern_per_answer(pattern_retriever):
    similar = pattern_retriever.similar_questions("staj kaç gün sürüyor", limit=5)

    assert similar[0] == "Yaz stajı kaç gün?"
    assert set(similar) >= {"Staj zorunlu mu?"}
    assert sum("sigorta" in question for question in similar) == 1
    assert "Bölüm başkanı kim?" not in similar


def test_similar_questions_offer_one_pattern_per_shape(pattern_retriever):
    similar = pattern_retriever.similar_questions("akts bilgisi", limit=5)

    assert sum("AKTS" in question for question in similar) == 1


def test_unrelated_questions_get_no_suggestions(pattern_retriever):
    # Ortak içerik sözcüğü yok ve hiçbir kalıba anlamca yakın değil.
    assert pattern_retriever.similar_questions("Yemekhane menüsü ne?", limit=5) == []


def test_similar_questions_need_the_question_index(store, embedder):
    retriever = HybridRetriever(store, embedder, top_k=3, max_chars=100_000)
    assert retriever.similar_questions("herhangi", limit=5) == []


def test_the_same_text_enters_the_context_once(store, questions, embedder):
    retriever = HybridRetriever(store, embedder, top_k=6, max_chars=100_000, questions=questions)
    texts = [document.text for document in retriever.retrieve("akademik kadroda kimler var?")]
    assert len(texts) == len(set(texts))


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


def test_lexical_search_matches_synonyms():
    documents = [
        Document(id="1", title="SE212", text="Ön koşul: SE112", **_META),
        Document(id="2", title="SE212", text="AKTS: 6", **_META),
    ]
    assert LexicalIndex(documents).search("ön şartı ne", 1)[0].id == "1"


def test_lexical_index_knows_the_course_codes_in_its_documents():
    documents = [
        Document(id="1", title="MATH276", text="MATH276 — Diferansiyel Denklemler", **_META),
        Document(id="2", title="SE 212", text="Ön koşul: SE 112", **_META),
    ]
    assert LexicalIndex(documents).course_codes == {"math276", "se212", "se112"}
