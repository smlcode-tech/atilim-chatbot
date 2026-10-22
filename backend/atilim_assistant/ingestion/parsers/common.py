"""Tüm ayrıştırıcıların kullandığı belge ve hazır yanıt fabrikaları.

Her ayrıştırıcı bir kaynağın belgelerini ve hazır yanıtlarını aynı biçimde üretir; kaynak
bilgisi (kimlik, başlık, adres, birim) her nesneye buradan kopyalanır. Bu iki işlev daha önce
her ayrıştırıcıda ayrı ayrı tanımlıydı; tek yerde durmaları, alanların bütün kaynaklarda aynı
doldurulmasını sağlar.
"""

from atilim_assistant.domain import Document, PreparedAnswer, Source


def doc_for(source: Source, local_id: str, title: str, text: str) -> Document:
    """Kaynağın bir belgesi. Kimlik `<kaynak>:<yerel kimlik>` biçimindedir ve sayfa içeriğinden
    türetilir; yeniden indekslemede aynı kalır."""
    return Document(
        id=f"{source.id}:{local_id}",
        source_id=source.id,
        source_title=source.title,
        url=source.url,
        unit=source.unit,
        category=source.category,
        title=title,
        text=text,
    )


def answer_for(source: Source, questions: list[str], answer: str) -> PreparedAnswer:
    """Kaynağın bir hazır yanıtı; kaynak sayfa yanıtla birlikte gösterilir."""
    return PreparedAnswer(
        source_id=source.id,
        source_title=source.title,
        url=source.url,
        questions=questions,
        answer=answer,
    )
