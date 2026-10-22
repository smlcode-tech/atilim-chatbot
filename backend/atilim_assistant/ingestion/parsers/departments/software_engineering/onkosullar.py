"""Ders ön koşul zincirini belgeler ve hazır yanıtlara çevirir.

Girdi: `data/onkosullar.txt` dosyası — her satır `DERS: ÖNKOŞUL1, ÖNKOŞUL2` biçiminde.
"""

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.ingestion.parsers.common import answer_for, doc_for


def parse(text: str, source: Source) -> SourceContent:
    """Zinciri iki yönde belgeler: "X'in ön koşulu ne?" ve "X'i geçince ne açılır?". İkinci
    yön sayfada doğrudan yazmaz; ters indeksle hesaplanır, yoksa model zincirin tamamını
    tarayıp kendisi çıkarmak zorunda kalırdı. HTML değil düz metin alır (bkz. modül açıklaması)."""
    prerequisites: dict[str, list[str]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        course, _, prereq_str = line.partition(":")
        course = course.strip()
        prereqs = [p.strip() for p in prereq_str.split(",") if p.strip()]
        if course and prereqs:
            prerequisites[course] = prereqs

    if not prerequisites:
        raise ValueError(f"{source.id}: ön koşul verisi bulunamadı.")

    # Ters indeks: hangi ders hangi derslerin kapısını açar
    unlocks: dict[str, list[str]] = {}
    for course, prereqs in prerequisites.items():
        for prereq in prereqs:
            unlocks.setdefault(prereq, []).append(course)

    documents: list[Document] = []
    answers: list[PreparedAnswer] = []

    # Özet belgesi
    lines = [f"{source.unit} — Ders Ön Koşul Zinciri (2024-2025)\n"]
    for course, prereqs in sorted(prerequisites.items()):
        prereq_str = " ve ".join(prereqs)
        lines.append(f"{course} alabilmek için ön koşul: {prereq_str}")
    summary = "\n".join(lines)
    documents.append(doc_for(source, "ozet", source.title, summary))
    answers.append(
        answer_for(
            source,
            [
                "Ön koşul zinciri nedir?",
                "Derslerin ön koşulları nelerdir?",
                f"{source.unit} ön koşul tablosu",
                "Hangi dersi almak için hangi ders gerekli?",
                "Ön şartlı dersler listesi",
                "Hangi derslerin ön koşulu var?",
            ],
            summary,
        )
    )

    # Her ders için: ön koşul belgesi
    for course, prereqs in sorted(prerequisites.items()):
        prereq_str = " ve ".join(prereqs)
        doc_text = (
            f"{course} dersi ön koşulları ({source.unit}):\n"
            f"{course} dersini alabilmek için önce {prereq_str} dersini/derslerini başarıyla tamamlamış olmak gerekir."
        )
        if course in unlocks:
            unlocked = ", ".join(sorted(unlocks[course]))
            doc_text += f"\n{course} tamamlandıktan sonra açılan dersler: {unlocked}"
        documents.append(doc_for(source, f"onkosul-{course.lower()}", f"{course} Ön Koşulu", doc_text))
        answers.append(
            answer_for(
                source,
                [
                    f"{course} dersinin ön koşulu nedir?",
                    f"{course} alabilmek için ne gerekir?",
                    f"{course} öncesinde hangi dersi almam lazım?",
                    f"{course} almadan önce hangi dersi geçmeliyim?",
                    f"{course} ön şartı var mı?",
                ],
                doc_text,
            )
        )

    # Her ön koşul dersi için: hangi dersleri açtığı belgesi
    for prereq, courses in sorted(unlocks.items()):
        courses_str = ", ".join(sorted(courses))
        doc_text = (
            f"{prereq} dersini tamamlayanlar için açılan dersler ({source.unit}):\n"
            f"{prereq} başarıyla tamamlandığında şu dersler alınabilir: {courses_str}"
        )
        documents.append(doc_for(source, f"acar-{prereq.lower()}", f"{prereq} Sonrası Açılan Dersler", doc_text))
        answers.append(
            answer_for(
                source,
                [
                    f"{prereq} sonrasında hangi dersler açılır?",
                    f"{prereq} hangi derslerin ön koşuludur?",
                    f"{prereq} aldıktan sonra ne alabilirim?",
                    f"{prereq} geçince hangi derslere kaydolabilirim?",
                    f"{prereq} kalırsam hangi dersleri alamam?",
                ],
                doc_text,
            )
        )

    return SourceContent(documents=documents, prepared_answers=answers)
