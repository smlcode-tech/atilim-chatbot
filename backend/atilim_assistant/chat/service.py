"""Soru-cevap akışı: ilgili belgeleri getir, modele sor, kaynaklarıyla birlikte döndür."""

from atilim_assistant.chat.prompts import SYSTEM_PROMPT, build_prompt
from atilim_assistant.domain import Answer, Citation, Document
from atilim_assistant.ports import ChatModel
from atilim_assistant.retrieval.retriever import HybridRetriever


class ChatService:
    def __init__(self, retriever: HybridRetriever, model: ChatModel) -> None:
        self._retriever = retriever
        self._model = model

    def answer(self, question: str) -> Answer:
        documents = self._retriever.retrieve(question)
        text = self._model.generate(SYSTEM_PROMPT, build_prompt(question, documents)).strip()
        if not text:
            raise RuntimeError("Model boş yanıt döndürdü.")
        return Answer(text=text, citations=_citations(documents))


def _citations(documents: list[Document]) -> list[Citation]:
    """Getirilen belgelerin geldiği sayfalar; aynı sayfa bir kez listelenir."""
    pages = {document.url: document.source_title for document in documents}
    return [Citation(title=title, url=url) for url, title in pages.items()]
