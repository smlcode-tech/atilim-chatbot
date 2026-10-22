"""Embedder arayüzünün Voyage AI uygulaması.

voyage-multilingual-2 modeli Türkçe dahil 100+ dili destekler.

Model değişirse indeks yeniden kurulmalıdır: farklı modellerin vektörleri karşılaştırılamaz
(bkz. `DocumentStore`'daki denetim).
"""

import logging
import time

import voyageai

logger = logging.getLogger(__name__)

# Tek istekte gönderilen metin sayısı. Voyage'ın liste sınırı 1000'dir; modelin istek başına
# toplam token sınırı da olduğundan partiler bunun çok altında tutulur.
_EMBED_BATCH_SIZE = 128
# İstekler arası minimum bekleme (saniye); kota aşımına karşı koruma.
_INTER_BATCH_DELAY = 0.2
# İstemci varsayılan olarak hiç beklemez ve hiç yeniden denemez: tek bir ağ takılması sohbet
# isteğini süresiz askıda bırakır, tek bir 429 da aramayı düşürürdü.
_TIMEOUT_SECONDS = 20
_MAX_RETRIES = 3


class VoyageEmbedder:
    """`Embedder` portunun Voyage uygulaması.

    Belgeler ve sorgular farklı `input_type` ile embedding'lenir: Voyage her birinin başına
    aramaya yönelik ayrı bir talimat ekler ("Represent the query for retrieving supporting
    documents" / "…the document for retrieval"). Kısa bir soru ile onu yanıtlayan uzun bir
    paragraf böylece birbirine daha yakın düşer.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = voyageai.Client(
            api_key=api_key, timeout=_TIMEOUT_SECONDS, max_retries=_MAX_RETRIES
        )
        self._model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Ingest'te indekslenecek metinler; parti parti, sırası korunarak gönderilir."""
        vectors: list[list[float]] = []
        batches = range(0, len(texts), _EMBED_BATCH_SIZE)
        for i, start in enumerate(batches):
            if i > 0:
                time.sleep(_INTER_BATCH_DELAY)
            batch = texts[start : start + _EMBED_BATCH_SIZE]
            result = self._client.embed(batch, model=self._model, input_type="document")
            vectors += result.embeddings
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Sohbette kullanıcının sorgusu; soru başına bir çağrı."""
        result = self._client.embed([text], model=self._model, input_type="query")
        return result.embeddings[0]
