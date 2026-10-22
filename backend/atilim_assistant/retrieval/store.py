"""Belgelerin ve vektörlerinin tutulduğu kalıcı depo (Chroma).

Chroma'ya yalnızca bu dosya dokunur; uygulamanın geri kalanı `Document` nesneleriyle çalışır.
Depo değişirse yalnızca bu sınıf yeniden yazılır.
"""

from dataclasses import asdict
from pathlib import Path

import chromadb

from atilim_assistant.domain import Document


class DocumentStore:
    """Tek bir Chroma koleksiyonu. Uygulamada iki tane kurulur: sayfa belgeleri (`collection`)
    ve soru kalıpları (`<collection>_questions`).

    `embed_model` koleksiyonun üst verisine yazılır ki indeksin hangi modelle kurulduğu
    sonradan bilinsin (aşağıdaki denetim).
    """

    def __init__(self, path: Path, collection: str, embed_model: str) -> None:
        client = chromadb.PersistentClient(path=str(path))
        # Uzay kosinüs seçilir: benzerlik eşikleri (`retriever._STRONG_SIMILARITY`) kosinüs
        # benzerliği olarak ölçüldü. Chroma'nın varsayılanı L2'dir ve uzay koleksiyon
        # oluşturulurken sabitlenir.
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
        """Bir kaynağın (sayfanın) tüm belgelerini yenileriyle değiştirir; diğer kaynaklara
        dokunmaz.

        Önce silinip sonra eklenir, güncelleme (upsert) yapılmaz: sayfadan kalkan bir bölümün
        eski belgesi upsert ile indekste kalır ve yanıtlarda eskimiş bilgi olarak çıkardı.
        """
        self._collection.delete(where={"source_id": source_id})
        if not documents:
            return
        self._collection.add(
            ids=[document.id for document in documents],
            documents=[document.text for document in documents],
            embeddings=embeddings,
            metadatas=[_to_metadata(document) for document in documents],
        )

    def search(self, embedding: list[float], limit: int) -> list[Document]:
        """En yakın belgeler, sıralı. RRF yalnızca sıraya baktığı için puan gerekmez."""
        return [document for document, _ in self.search_scored(embedding, limit)]

    def search_scored(self, embedding: list[float], limit: int) -> list[tuple[Document, float]]:
        """En yakın belgeler ve kosinüs benzerlikleri (1 en yakın).

        Chroma uzaklık döndürür; benzerliğe çevrilir ki eşikler ("en az 0.45") okunaklı olsun.
        """
        result = self._collection.query(query_embeddings=[embedding], n_results=limit)
        documents = _to_documents(result["ids"][0], result["documents"][0], result["metadatas"][0])
        return [(document, 1 - distance) for document, distance in zip(documents, result["distances"][0])]

    def count(self) -> int:
        """Belge sayısı. Açılışta boş indeks tespit edilir: sayfa indeksi boşsa uygulama
        başlamaz, kalıp indeksi boşsa arama onsuz sürer."""
        return self._collection.count()

    def all(self) -> list[Document]:
        """Tüm belgeler; BM25 indeksi bellekte kurulduğu için açılışta bir kez okunur."""
        result = self._collection.get()
        return _to_documents(result["ids"], result["documents"], result["metadatas"])


def _to_metadata(document: Document) -> dict[str, str]:
    """`Document`'ın Chroma üst verisi. `id` ve `text` Chroma'da ayrı alanlarda tutulur;
    üst veriye de yazılırsa metin iki kez saklanırdı."""
    metadata = asdict(document)
    del metadata["id"], metadata["text"]
    return metadata


def _to_documents(ids: list[str], texts: list[str], metadatas: list[dict]) -> list[Document]:
    """Chroma'nın sütun biçimindeki sonucunu (ayrı id, metin, üst veri listeleri) belgelere
    çevirir; `_to_metadata`'nın tersidir."""
    return [
        Document(id=id_, text=text, **metadata)
        for id_, text, metadata in zip(ids, texts, metadatas)
    ]
