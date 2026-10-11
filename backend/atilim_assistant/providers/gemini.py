"""Embedder ve ChatModel arayüzlerinin Google Gemini uygulaması."""

from google import genai
from google.genai import types

# Gemini embed_content tek istekte en fazla 100 metin kabul eder.
_EMBED_BATCH_SIZE = 100
_REQUEST_TIMEOUT_MS = 30_000


class GeminiProvider:
    def __init__(self, api_key: str, llm_model: str, embed_model: str, embed_dimensions: int) -> None:
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=_REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=4),
            ),
        )
        self._llm_model = llm_model
        self._embed_model = embed_model
        self._embed_dimensions = embed_dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH_SIZE):
            vectors += self._embed(texts[start : start + _EMBED_BATCH_SIZE], "RETRIEVAL_DOCUMENT")
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]

    def generate(self, system: str, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._llm_model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system, temperature=0),
        )
        return response.text or ""

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        response = self._client.models.embed_content(
            model=self._embed_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type, output_dimensionality=self._embed_dimensions
            ),
        )
        return [embedding.values for embedding in response.embeddings]
