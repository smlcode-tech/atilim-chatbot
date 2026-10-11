"""Dış model sağlayıcılarının uyması gereken arayüzler."""

from typing import Protocol


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class ChatModel(Protocol):
    def generate(self, system: str, prompt: str) -> str: ...
