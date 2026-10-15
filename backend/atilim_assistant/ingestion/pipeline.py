"""Bir kaynağı siteden alıp içeriğe çeviren ve indeksleyen adımlar."""

import httpx

from atilim_assistant.domain import Source, SourceContent
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
) -> None:
    """Kaynağın eski belgelerini ve hazır yanıtlarını yenileriyle değiştirir; diğer kaynaklara dokunmaz."""
    embeddings = embedder.embed_documents([document.text for document in content.documents])
    store.replace_source(source.id, content.documents, embeddings)
    prepared_answers.replace_source(source.id, content.prepared_answers)
