"""Belgelerin ve vektörlerinin tutulduğu kalıcı depo (Chroma)."""

from dataclasses import asdict
from pathlib import Path

import chromadb

from atilim_assistant.domain import Document


class DocumentStore:
    def __init__(self, path: Path, collection: str, embed_model: str) -> None:
        client = chromadb.PersistentClient(path=str(path))
        self._collection = client.get_or_create_collection(
            collection,
            metadata={"embed_model": embed_model},
            configuration={"hnsw": {"space": "cosine"}},
        )
        # Farklı embedding modellerinin vektörleri aynı uzayda değildir: eski indeksle sorgu ya
        # boyut hatası verir ya da sessizce alakasız belgeler getirir.
        indexed_with = (self._collection.metadata or {}).get("embed_model")
        if indexed_with != embed_model:
            if self._collection.count():
                raise RuntimeError(
                    f"İndeks '{indexed_with}' ile kurulmuş, ayarlardaki model '{embed_model}'. "
                    f"{path} dizinini silip `python -m atilim_assistant ingest` komutunu çalıştır."
                )
            self._collection.modify(metadata={"embed_model": embed_model})

    def replace_source(
        self, source_id: str, documents: list[Document], embeddings: list[list[float]]
    ) -> None:
        self._collection.delete(where={"source_id": source_id})
        self._collection.add(
            ids=[document.id for document in documents],
            documents=[document.text for document in documents],
            embeddings=embeddings,
            metadatas=[_to_metadata(document) for document in documents],
        )

    def search(self, embedding: list[float], limit: int) -> list[Document]:
        result = self._collection.query(query_embeddings=[embedding], n_results=limit)
        return _to_documents(result["ids"][0], result["documents"][0], result["metadatas"][0])

    def count(self) -> int:
        return self._collection.count()

    def all(self) -> list[Document]:
        result = self._collection.get()
        return _to_documents(result["ids"], result["documents"], result["metadatas"])


def _to_metadata(document: Document) -> dict[str, str]:
    metadata = asdict(document)
    del metadata["id"], metadata["text"]
    return metadata


def _to_documents(ids: list[str], texts: list[str], metadatas: list[dict]) -> list[Document]:
    return [
        Document(id=id_, text=text, **metadata)
        for id_, text, metadata in zip(ids, texts, metadatas)
    ]
