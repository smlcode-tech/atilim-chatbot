"""Dış model sağlayıcılarının ve kalıcı depoların uyması gereken arayüzler."""

from typing import Protocol

from atilim_assistant.domain import Completion, ConversationSummary, Turn


class UserRepository(Protocol):
    def upsert(self, google_sub: str, email: str, name: str) -> str:
        """Kullanıcıyı kaydeder ya da günceller; kullanıcı kimliğini döndürür."""
        ...

    def count_question(self, user_id: str, day: str) -> int:
        """O gün sorulan soru sayısını bir artırır ve yeni değeri döndürür.

        Gün değiştiğinde sayaç sıfırdan başlar.
        """
        ...

    def count_guest_question(self, guest_key: str, day: str) -> int:
        """Misafir için `count_question`; `guest_key` IP adresinin özetidir."""
        ...

    def questions_asked(self, user_id: str, day: str) -> int:
        """O gün sorulan soru sayısı; sayacı değiştirmez. Başka günün sayacı 0 sayılır."""
        ...

    def guest_questions_asked(self, guest_key: str, day: str) -> int:
        """Misafir için `questions_asked`."""
        ...

    def uncount_question(self, user_id: str, day: str) -> None:
        """`count_question`ın artırdığını geri alır: yanıtlanamayan soru sınırdan düşülmez."""
        ...

    def uncount_guest_question(self, guest_key: str, day: str) -> None:
        """Misafir için `uncount_question`."""
        ...


class ConversationRepository(Protocol):
    def start(self, user_id: str, title: str) -> str:
        """Yeni konuşma açar; kimliğini döndürür."""
        ...

    def add_turns(self, conversation_id: str, user_id: str, turns: list[Turn]) -> None: ...

    def turns(self, conversation_id: str, user_id: str) -> list[Turn] | None:
        """Konuşma yoksa ya da başkasına aitse None."""
        ...

    def list_for(self, user_id: str) -> list[ConversationSummary]: ...

    def delete(self, conversation_id: str, user_id: str) -> bool: ...


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class ChatModel(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        """OpenAI sohbet biçimindeki mesajlarla bir tur üretir; `tools` boşsa araç çağrılamaz."""
        ...
