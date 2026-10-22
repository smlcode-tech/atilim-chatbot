"""Dış model sağlayıcılarının ve kalıcı depoların uyması gereken arayüzler.

Uygulama somut sınıflara (Groq, Voyage, MongoDB) değil bu arayüzlere bağlıdır: sağlayıcı
değiştirmek yalnızca yeni bir bağdaştırıcı yazıp `bootstrap.py`'de bağlamaktır, testler de
ağa çıkmayan sahte uygulamalar verir. `Protocol` kullanılır, kalıtım gerekmez: aynı
yöntemlere sahip her sınıf arayüze uyar.
"""

from typing import Protocol

from atilim_assistant.domain import Completion, ConversationSummary, Turn


class UserRepository(Protocol):
    """Kullanıcı kayıtları ve günlük soru sayaçları."""

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
    """Girişli kullanıcıların konuşma geçmişi. Her yöntem `user_id` alır: depo, kullanıcının
    yalnızca kendi konuşmalarına erişmesini sağlamakla yükümlüdür."""

    def start(self, user_id: str, title: str) -> str:
        """Yeni konuşma açar; kimliğini döndürür."""
        ...

    def add_turns(self, conversation_id: str, user_id: str, turns: list[Turn]) -> None:
        """Turları konuşmanın sonuna ekler."""
        ...

    def turns(self, conversation_id: str, user_id: str) -> list[Turn] | None:
        """Konuşma yoksa ya da başkasına aitse None."""
        ...

    def list_for(self, user_id: str) -> list[ConversationSummary]:
        """Kullanıcının konuşmaları, en son güncellenen önce."""
        ...

    def delete(self, conversation_id: str, user_id: str) -> bool:
        """Silindiyse True; konuşma yoksa ya da başkasınınsa False."""
        ...


class Embedder(Protocol):
    """Metni vektöre çevirir. Belge ve sorgu ayrı yöntemlerdir: bazı modeller ikisini farklı
    işler ve bu ayrım arama kalitesini artırır."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """İndekslenecek metinler; sonuçlar girdiyle aynı sıradadır."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Arama sorgusu."""
        ...


class ChatModel(Protocol):
    """Araç çağırabilen sohbet modeli."""

    def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        """OpenAI sohbet biçimindeki mesajlarla bir tur üretir; `tools` boşsa araç çağrılamaz."""
        ...
