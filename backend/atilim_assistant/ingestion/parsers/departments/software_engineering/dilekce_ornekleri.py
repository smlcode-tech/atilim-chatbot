"""Dilekçe Örnekleri sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa: https://www.atilim.edu.tr/tr/se/page/5217/dilekce-ornekleri
İndirilebilir Word dosyaları (download_url) canlı sayfadan alınır.
Şablon metinleri (.doc/.docx) macOS-bağımlı araçlarla çıkarılmış ve
  doğrudan bu dosyada saklanmaktadır; şablonlar değişirse güncellenmeli.
"""

from bs4 import BeautifulSoup

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace

# ---------------------------------------------------------------------------
# Önceden çıkarılmış dilekçe şablon metinleri
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, str] = {
    "Ders Çakışma Dilekçesi": """\
T.C.
ATILIM ÜNİVERSİTESİ
MÜHENDİSLİK FAKÜLTESİ DEKANLIĞI
....................... MÜHENDİSLİĞİ BÖLÜM BAŞKANLIĞI

Bölümümüz ......................... numaralı öğrencilerinden \
.................................... 'ın .................................. dersi/dersleri çakışmaktadır.

Gereğini bilgilerinize rica ederim.

                                                              Saygılarımla,

                                                         Akademik Danışman


1. Dersin Öğretim Elemanı                    2. Dersin Öğretim Elemanı


Öğrenci İmza""",

    "Ders Çakışma Nedeniyle \"Makeup\" Sınavı Dilekçesi": """\
T.C.
ATILIM ÜNİVERSİTESİ
MÜHENDİSLİK FAKÜLTESİ DEKANLIĞI
....................... MÜHENDİSLİĞİ BÖLÜM BAŞKANLIĞI

                                                              …./…/…..

..................... …………………… BAŞKANLIĞINA

Bölümünüz ......................... numaralı …… sınıf öğrencisiyim. \
20…../20…… Akademik Yılı Güz/Bahar Döneminde almış olduğum dersin/derslerinin \
sınavı/sınavları ……..………. tarihinde çakışmaktadır. \
Söz konusu çakışma sebebiyle ………………….. dersinden makeup sınavı talep etmekteyim.

Gereğini arz ederim.

                                                              Saygılarımla,

Ad SOYAD


1. Dersin Hocası İmza                        2. Dersin Hocası İmza""",

    "Kayıt Dondurma Dilekçesi": """\
ATILIM ÜNİVERSİTESİ
Mühendislik Fakültesi Dekanlığı
…………………………………………………………….. Bölüm Başkanlığına

…./ ….../ 20..

Bölümünüz ……………………….. numaralı öğrencisiyim. \
20.. / 20.. Akademik Yılı …………….. döneminde \
……………………………………………………………………………………………………………………………………………………………\
nedeniyle/nedenlerle izinli sayılmak (kayıt dondurmak) istiyorum.

Olurlarınıza ve onayınıza saygılarımla arz ederim.

                                                         Öğrencinin;
Adı Soyadı:
İmzası:

Öğrencinin;
Telefon Numarası: +90
Posta (Yazışma) Adresi:""",
}


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    # Sayfadaki güncel download linklerini al
    links: dict[str, str] = {}
    for a in container.find_all("a"):
        title = collapse_whitespace(a.get_text())
        href = a.get("href", "").strip()
        if title and href and any(href.endswith(ext) for ext in (".doc", ".docx", ".pdf")):
            links[title] = href

    documents: list[Document] = []
    answers: list[PreparedAnswer] = []

    # Özet: tüm dilekçe listesi + linkler
    summary_lines = [f"{source.unit} — Dilekçe Örnekleri\n"]
    for title, url in links.items():
        summary_lines.append(f"- {title}: {url}")
    summary = "\n".join(summary_lines)
    documents.append(_doc(source, "ozet", source.title, summary))
    answers.append(
        _answer(
            source,
            [
                "Dilekçe örnekleri nerede?",
                "Hangi dilekçe örnekleri var?",
                "Staj veya ders ile ilgili dilekçe nereden indirilir?",
                "Bölümün resmi dilekçeleri nelerdir?",
                "Dilekçe formları, şablonları nereden indirilir?",
                "Bölüme dilekçe nasıl verilir?",
            ],
            summary,
        )
    )

    # Her dilekçe için belge: şablon metni + indirme linki
    for title, download_url in links.items():
        template = _TEMPLATES.get(title, "")
        doc_text = f"{title}\n"
        doc_text += f"İndir (Word): {download_url}\n\n"
        if template:
            doc_text += "Dilekçe Şablonu:\n\n" + template
        else:
            doc_text += "(Şablon metni mevcut değil; lütfen yukarıdaki linkten Word dosyasını indirin.)"

        slug = _slugify(title)
        documents.append(_doc(source, slug, title, doc_text))
        answers.append(
            _answer(
                source,
                _questions(title, download_url),
                doc_text,
            )
        )

    return SourceContent(documents=documents, prepared_answers=answers)


def _slugify(title: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ\"", "cgiosucgiOSU_")
    return title.lower().translate(tr).replace(" ", "-")[:40]


def _questions(title: str, url: str) -> list[str]:
    base = title.rstrip(".")
    subject = base.removesuffix("Dilekçesi").strip()
    return [
        f"{base} nasıl yazılır?",
        f"{base} şablonu nedir?",
        f"{base} nereden indirilir?",
        f"{base} için ne yapmalıyım?",
        # Öğrenciler dilekçeyi çoğu zaman konusuyla anar: "kayıt dondurma formu".
        f"{subject} formu, belgesi nereden bulunur?",
        f"{subject} için nasıl başvururum?",
    ]


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
