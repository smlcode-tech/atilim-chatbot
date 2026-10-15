"""Ortak Eğitim sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container):
  - <strong> ile başlayan paragraflar soru, hemen ardından gelen <p> paragrafları yanıt.
  - Sayfanın alt kısmında müfredat detaylarını içeren bir tablo bulunur.
"""

from bs4 import BeautifulSoup, NavigableString, Tag

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    qa_pairs = _extract_qa(container)
    table_text = _extract_table(container)

    documents: list[Document] = []
    answers: list[PreparedAnswer] = []

    # Özet: tüm içerik tek belge
    all_parts = [f"{source.unit} — Ortak Eğitim Programı\n"]
    for q, a in qa_pairs:
        all_parts.append(f"**{q}**\n{a}")
    if table_text:
        all_parts.append(table_text)
    summary = "\n\n".join(all_parts)
    documents.append(_doc(source, "ozet", source.title, summary))
    answers.append(
        _answer(
            source,
            [
                "Ortak eğitim nedir?",
                "Ortak eğitim programı hakkında bilgi",
                f"{source.unit} ortak eğitim",
                "Co-op programı nedir?",
            ],
            summary,
        )
    )

    # Her S&C çifti için ayrı belge ve hazır yanıt
    for i, (q, a) in enumerate(qa_pairs):
        doc_text = f"{q}\n\n{a}"
        documents.append(_doc(source, f"soru-{i + 1}", q, doc_text))
        answers.append(_answer(source, [q], doc_text))

    # Tablo ayrı belge
    if table_text:
        documents.append(_doc(source, "tablo", "Ortak Eğitim Müfredat Tablosu", table_text))

    return SourceContent(documents=documents, prepared_answers=answers)


def _extract_qa(container: Tag) -> list[tuple[str, str]]:
    """<strong> içeren <p> → soru, hemen ardından gelen <p> → yanıt."""
    pairs: list[tuple[str, str]] = []
    # İçerik genellikle div.col-md-12 içinde; yoksa container'ın kendisi taranır.
    inner = container.find("div", class_="col-md-12") or container
    children = [c for c in inner.children if isinstance(c, Tag)]
    i = 0
    while i < len(children):
        el = children[i]
        strong = el.find("strong") if el.name == "p" else None
        if strong:
            question = collapse_whitespace(strong.get_text())
            # Ardından gelen boş olmayan <p>'leri yanıt olarak topla
            answer_parts = []
            j = i + 1
            while j < len(children):
                nxt = children[j]
                # Bir sonraki soru başlığına ulaşıldıysa dur
                if nxt.name == "p" and nxt.find("strong"):
                    break
                if nxt.name in ("p", "ul", "ol"):
                    text = collapse_whitespace(nxt.get_text(" "))
                    if text:
                        answer_parts.append(text)
                elif nxt.name == "table":
                    break
                j += 1
            answer = " ".join(answer_parts)
            if question and answer:
                pairs.append((question, answer))
            i = j
        else:
            i += 1
    return pairs


def _extract_table(container: Tag) -> str:
    """Müfredat tablosunu düz metin satırlarına çevirir."""
    inner = container.find("div", class_="col-md-12") or container
    table = inner.find("table")
    if not table:
        return ""
    lines = ["Ortak Eğitim Müfredat Tablosu:"]
    for row in table.find_all("tr"):
        cells = [collapse_whitespace(c.get_text()) for c in row.find_all(["td", "th"])]
        cells = [c for c in cells if c]
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def _doc(source: Source, local_id: str, title: str, text: str) -> Document:
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


def _answer(source: Source, questions: list[str], answer: str) -> PreparedAnswer:
    return PreparedAnswer(
        source_id=source.id,
        source_title=source.title,
        url=source.url,
        questions=questions,
        answer=answer,
    )
