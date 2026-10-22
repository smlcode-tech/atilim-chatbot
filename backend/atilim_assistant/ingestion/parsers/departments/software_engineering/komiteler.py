"""Komiteler sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - İki sütunlu tablo: Komite Adı | Üyeler
  - İlk iki satır birleşik başlık ve sütun adlarıdır.
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace


def parse(html: str, source: Source) -> SourceContent:
    """Tüm komiteler tek belgede; hazır yanıtlar hem toplu hem komite başına üretilir, çünkü
    öğrenci genellikle tek bir komiteyi ("staj komitesinde kim var?") sorar."""
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    # Başlık satırını ve sütun adları satırını atla (colspan=2 veya "Komite Adı" içeren)
    committees: list[tuple[str, str]] = []
    for row in container.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 2:
            continue
        name = collapse_whitespace(cells[0].get_text())
        members = collapse_whitespace(cells[1].get_text())
        if name and name not in ("Komite Adı", "Komite Üyeleri"):
            committees.append((name, members))

    if not committees:
        raise ValueError(f"{source.url} sayfasında komite tablosu bulunamadı.")

    # Dönem başlığını tablo ilk satırındaki colspan=2 hücreden al
    period_cell = container.find("td", attrs={"colspan": "2"})
    period = collapse_whitespace(period_cell.get_text()) if period_cell else ""

    lines = [period or source.title]
    for name, members in committees:
        lines.append(f"- {name}: {members}")
    roster_text = "\n".join(lines)

    doc = _doc(source, "liste", source.title, roster_text)

    answers: list[PreparedAnswer] = [
        _answer(
            source,
            [
                f"{source.unit} komiteleri nelerdir?",
                "Bölüm komitesi üyeleri kimler?",
                "Yazılım mühendisliği bölüm komiteleri",
                "Bölümde hangi komisyonlar var, kimler görevli?",
                "Komitelerde hangi hocalar görev alıyor?",
            ],
            roster_text,
        )
    ]

    # Her komite için ayrı hazır yanıt
    for name, members in committees:
        answers.append(
            _answer(
                source,
                [
                    f"{name} komitesi kimlerden oluşuyor?",
                    f"{name} komitesi üyeleri kimler?",
                    f"{name} komitesinde kimler var?",
                    f"{name} komisyonunda hangi hocalar görevli?",
                    f"{name} komitesinden kim sorumlu, kime başvurmalıyım?",
                ],
                f"**{name} komitesi:** {members}",
            )
        )

    return SourceContent(documents=[doc], prepared_answers=answers)


def _doc(source: Source, local_id: str, title: str, text: str) -> Document:
    """Bu kaynağın bir belgesi. Kimlik `<kaynak>:<yerel kimlik>` biçimindedir ve sayfa
    içeriğinden türetilir; yeniden indekslemede aynı kalır."""
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
    """Bu kaynağın bir hazır yanıtı; kaynak sayfa yanıtla birlikte gösterilir."""
    return PreparedAnswer(
        source_id=source.id,
        source_title=source.title,
        url=source.url,
        questions=questions,
        answer=answer,
    )
