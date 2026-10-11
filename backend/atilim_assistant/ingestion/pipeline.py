"""Bir kaynağı siteden alıp belgelere çeviren ve indeksleyen adımlar."""

import httpx

from atilim_assistant.domain import Document, Source
from atilim_assistant.ports import Embedder
from atilim_assistant.retrieval.store import DocumentStore

_USER_AGENT = "AtilimAssistantBot/0.1 (+https://www.atilim.edu.tr)"


def fetch_html(url: str) -> str:
    response = httpx.get(
        url, headers={"User-Agent": _USER_AGENT}, timeout=30, follow_redirects=True
    )
    response.raise_for_status()
    return response.text


def load_documents(source: Source, html: str | None = None) -> list[Document]:
    """`html` verilmezse sayfa siteden çekilir; verilirse (hata ayıklama) doğrudan o ayrıştırılır."""
    return source.parser(html if html is not None else fetch_html(source.url), source)


def index_documents(
    source: Source, documents: list[Document], embedder: Embedder, store: DocumentStore
) -> None:
    """Kaynağın indeksteki eski belgelerini yenileriyle değiştirir; diğer kaynaklara dokunmaz."""
    embeddings = embedder.embed_documents([document.text for document in documents])
    store.replace_source(source.id, documents, embeddings)
