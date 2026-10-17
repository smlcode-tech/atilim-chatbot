"""Bir kaynağı siteden alıp içeriğe çeviren ve indeksleyen adımlar."""

import httpx

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.ports import Embedder
from atilim_assistant.retrieval.prepared import PreparedAnswerStore
from atilim_assistant.retrieval.store import DocumentStore

_USER_AGENT = "AtilimAssistantBot/0.1 (+https://www.atilim.edu.tr)"


def fetch_html(url: str) -> str:
    response = httpx.get(
        url, headers={"User-Agent": _USER_AGENT}, timeout=30, follow_redirects=True
    )
    response.raise_for_status()
    return response.text


def load_content(source: Source, html: str | None = None) -> SourceContent:
    """`html` verilmezse sayfa siteden çekilir; verilirse (hata ayıklama) doğrudan o ayrıştırılır.
    `source.local_content_path` tanımlıysa ağ isteği yapılmaz, dosya okunur."""
    if html is not None:
        raw = html
    elif source.local_content_path is not None:
        raw = source.local_content_path.read_text(encoding="utf-8")
    else:
        raw = fetch_html(source.url)
    return source.parser(raw, source)


def index_content(
    source: Source,
    content: SourceContent,
    embedder: Embedder,
    store: DocumentStore,
    prepared_answers: PreparedAnswerStore,
    questions: DocumentStore,
) -> None:
    """Kaynağın eski belgelerini ve hazır yanıtlarını yenileriyle değiştirir; diğer kaynaklara dokunmaz."""
    embeddings = embedder.embed_documents([document.text for document in content.documents])
    store.replace_source(source.id, content.documents, embeddings)
    prepared_answers.replace_source(source.id, content.prepared_answers)

    entries = question_documents(source, content.prepared_answers)
    question_embeddings = embedder.embed_documents([entry.title for entry in entries])
    questions.replace_source(source.id, entries, question_embeddings)


def question_documents(source: Source, answers: list[PreparedAnswer]) -> list[Document]:
    """Her soru kalıbı için, kalıbın kendisiyle aranan ve yanıtı taşıyan bir belge.

    Sayfa belgeleri sitenin dilindedir ("Telefon: +90…"), kullanıcı ise kendi dilinde sorar
    ("hocalara nasıl ulaşırım?"). Soru kalıpları kullanıcı dilinde yazıldığı için, onlarla
    yapılan anlamsal arama aynı şeyi başka sözcüklerle soranları da doğru yanıta götürür.
    """
    return [
        Document(
            id=f"{source.id}:hazir-{answer_index}-{question_index}",
            source_id=source.id,
            source_title=answer.source_title,
            url=answer.url,
            unit=source.unit,
            category=source.category,
            title=question,
            text=answer.answer,
        )
        for answer_index, answer in enumerate(answers)
        for question_index, question in enumerate(answer.questions)
    ]
