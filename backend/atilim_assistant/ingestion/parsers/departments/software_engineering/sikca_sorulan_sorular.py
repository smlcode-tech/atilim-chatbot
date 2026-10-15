"""Sıkça Sorulan Sorular sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - <p><strong>Soru metni</strong></p> ardından bir veya birden fazla <p>cevap</p>
  - Son bölümde Erasmus ortağı üniversitelerin iki sütunlu tablosu (Üniversite | Ülke)
"""

from bs4 import BeautifulSoup, Tag

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    col = container.find(class_="col-md-12") or container

    qa_pairs = _extract_qa(col)
    erasmus = _extract_erasmus(col)

    if not qa_pairs:
        raise ValueError(f"{source.url} sayfasında soru-cevap çifti bulunamadı.")

    documents: list[Document] = []
    answers: list[PreparedAnswer] = []

    # Erasmus sorusunun cevabı "aşağıda verilmiştir" der; liste ise ayrı bir tablodadır.
    if erasmus:
        listing = "\n".join(f"- {uni} ({country})" for uni, country in erasmus)
        qa_pairs = [
            (question, f"{answer}\n\n{listing}" if "erasmus" in question.lower() else answer)
            for question, answer in qa_pairs
        ]

    # Her soru-cevap çifti kendi belgesi olur; hazır yanıt da üretilir.
    for i, (question, answer_text) in enumerate(qa_pairs):
        doc_text = f"S: {question}\nC: {answer_text}"
        documents.append(_doc(source, f"sss-{i + 1}", question[:80], doc_text))
        answers.append(
            _answer(
                source,
                [question],
                answer_text,
            )
        )

    # Erasmus tablosu
    if erasmus:
        lines = [f"{source.unit} Erasmus ortağı üniversiteler:"]
        for uni, country in erasmus:
            lines.append(f"- {uni} ({country})")
        erasmus_text = "\n".join(lines)
        documents.append(_doc(source, "erasmus", "Erasmus Ortağı Üniversiteler", erasmus_text))
        answers.append(
            _answer(
                source,
                [
                    f"{source.unit} Erasmus ortağı üniversiteler hangileri?",
                    "Yazılım mühendisliği Erasmus anlaşmaları olan üniversiteler neler?",
                    "Erasmus kapsamında hangi ülkelere gidebilirim?",
                    "Erasmus+ ortakları neler?",
                ],
                erasmus_text,
            )
        )

    return SourceContent(documents=documents, prepared_answers=answers)


def _extract_qa(col: Tag) -> list[tuple[str, str]]:
    """Soru (<strong> içinde) ve ardından gelen cevap paragraflarını çifter çıkarır."""
    qa: list[tuple[str, str]] = []
    current_question: str | None = None
    current_answer_parts: list[str] = []

    def _flush() -> None:
        if current_question and current_answer_parts:
            qa.append((current_question, "\n\n".join(current_answer_parts)))

    for child in col.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "table":
            break
        if child.name != "p":
            continue
        # Sayfada bir sonraki soru bazen önceki cevabın paragrafının sonunda, <br> ardından
        # <strong> içinde durur; paragraf soru başlıklarında bölünür.
        pending: list[str] = []
        for node in child.children:
            if isinstance(node, Tag) and node.name == "strong" and _is_question(node):
                text = collapse_whitespace(" ".join(pending))
                if text and current_question is not None:
                    current_answer_parts.append(text)
                _flush()
                current_question = collapse_whitespace(node.get_text())
                current_answer_parts = []
                pending = []
            else:
                pending.append(node.get_text(" ") if isinstance(node, Tag) else str(node))
        text = collapse_whitespace(" ".join(pending))
        if text and current_question is not None:
            current_answer_parts.append(text)
    _flush()
    return qa


def _is_question(strong: Tag) -> bool:
    return collapse_whitespace(strong.get_text()).endswith("?")


def _extract_erasmus(col: Tag) -> list[tuple[str, str]]:
    """Erasmus üniversite-ülke tablosunu çıkarır."""
    rows: list[tuple[str, str]] = []
    for table in col.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) != 2:
                continue
            uni = collapse_whitespace(cells[0].get_text())
            country = collapse_whitespace(cells[1].get_text())
            if uni and uni != "Üniversite":
                rows.append((uni, country))
        if rows:
            break
    return rows


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
