"""Yaz Stajları sayfasını belgeler ve hazır yanıtlara çevirir.

Sayfa yapısı (div.detail-container > div.col-md-12):
  - Büyük harfli <p> etiketleri bölüm başlığı, ardından gelen <ol> liste içeriği.
  - "Staj Prosedürü" başlığı altındaki görsel sunucu tarafında korumalı olduğundan
    adımlar bu dosyadaki sabit metinden alınmıştır.
"""

from bs4 import BeautifulSoup, Tag

from atilim_assistant.domain import Document, PreparedAnswer, Source, SourceContent
from atilim_assistant.text import collapse_whitespace

# Görsel olarak sunulan prosedür adımları sayfa metninden türetilmiştir.
_PROSEDUR_ADIMLARI = """\
Yaz Stajı Prosedür Adımları (SE Bölümü):

1. Staj yeri bul ve staj kabul belgesi (antetli, imzalı) al.
2. Staj başlangıcından en az 20 gün önce başvuruyu tamamla.
3. Staj Zorunluluk Belgesi'ni doldur, yazıcıdan çıkar; bölüm sekreterliğine \
(Yasemin Kurt) imza için teslim et.
4. Sigorta için gerekli belgeler (staj kabul belgesi × 2, kimlik fotokopisi, \
Google formu) bölüm sekreterliğine stajdan en az 10 gün önce teslim edilmeli.
5. Personel Müdürlüğü'nden işe giriş bildirgesi al (stajdan 1–20 iş günü önce); \
e-posta ile de alınabilir.
6. Stajı yap: SE399 için minimum 20 iş günü, SE499 için minimum 30 iş günü. \
Yaz okulu çakışırsa staj süresi uzatılmalı; aksi halde staj geçersiz sayılır.
7. Staj bitiminde Staj Değerlendirme Formu ve Kurum Anketi'ni şirkete doldurt; \
mühürlü ve kapalı zarfla bölüm sekreterliğine ulaştır.
8. Staj raporunu (ön sayfa dahil, Guidelines and Format of the Report'a uygun) \
Moodle üzerinden SE399/SE499 dersine yükle.
9. Stajı takip eden sonbahar döneminde SE399 veya SE499 dersine kayıt yaptır. \
Sonbahar'da kayıt olunmazsa ilkbahar dönemi denenir; o da geçilirse staj tekrarlanır.\
"""

# Sayfadaki tüm bölüm başlıkları → (slug, başlık, sorular)
_SECTIONS_META: dict[str, tuple[str, str, list[str]]] = {
    "STAJ ÖNERİLERİ BİLGİ DOSYASI İÇİN TIKLAYINIZ.": (
        "genel",
        "Yaz Stajı Genel Bilgi",
        [
            "Yaz stajı nedir?",
            "SE399 ve SE499 stajları hakkında bilgi",
            "Yaz stajı kaç gün?",
            "Staj zorunlu mu?",
            "Staj yapmak zorunda mıyım?",
            "Staj koordinatörü kim?",
            "Staj yaparken yaz okulu alınabilir mi?",
            "Kaç iş günü staj yapmam gerekiyor?",
            "Staj mecburi mi, kaç staj var?",
            "Staj sorumlusu, staj komisyonu kim?",
        ],
    ),
    "STAJ BAŞVURUSU İÇİN GEREKLİ BELGELER": (
        "basvuru-belgeler",
        "Staj Başvurusu İçin Gerekli Belgeler",
        [
            "Staj başvurusu için hangi belgeler gerekli?",
            "Staj zorunluluk belgesi nedir?",
            "Staja başvurmak için ne yapmalıyım?",
            "Staj için hangi evraklar, dokümanlar isteniyor?",
        ],
    ),
    "SIGORTA İÇİN GEREKLİ BELGELER": (
        "sigorta-belgeler",
        "Sigorta İçin Gerekli Belgeler",
        [
            "Staj sigortası için hangi belgeler lazım?",
            "Staj sigortası nasıl yapılır?",
            "Sigorta için hangi evrakları hazırlamalıyım?",
            "Stajda SGK sigortası için gereken belgeler neler?",
        ],
    ),
    "SIGORTA İÇİN BAŞVURU SÜRECİ": (
        "sigorta-surec",
        "Sigorta İçin Başvuru Süreci",
        [
            "Staj sigortası başvuru süreci nasıl?",
            "İşe giriş bildirgesi nasıl alınır?",
            "Staj için ne zaman sigorta başvurusu yapmalıyım?",
            "SGK işe giriş belgesi ne zaman ve nasıl çıkar?",
        ],
    ),
    "STAJ BİTİŞİNDE GEREKLİ BELGELER": (
        "bitis-belgeler",
        "Staj Bitişinde Gerekli Belgeler",
        [
            "Staj bitiminde ne yapmalıyım?",
            "Staj raporu nasıl teslim edilir?",
            "SE399 veya SE499 dersine nasıl kayıt olunur?",
            "Staj değerlendirme formu nasıl doldurulur?",
            "Staj bitince hangi belgeleri teslim etmeliyim?",
            "Staj raporunu ne zaman, nereye teslim ederim?",
        ],
    ),
}


def parse(html: str, source: Source) -> SourceContent:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(class_="detail-container")
    if not container:
        raise ValueError(f"{source.url} sayfasında detail-container bulunamadı.")

    inner = container.find("div", class_="col-md-12") or container
    children = [c for c in inner.children if isinstance(c, Tag)]

    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_items: list[str] = []

    for el in children:
        if el.name == "p":
            text = collapse_whitespace(el.get_text())
            if not text or text == "Staj Prosedürü":
                continue
            # Bilinen bölüm başlıklarından biri mi?
            if text in _SECTIONS_META:
                if current_heading is not None and current_items:
                    sections.append((current_heading, current_items))
                current_heading = text
                current_items = []
        elif el.name in ("ol", "ul") and current_heading is not None:
            items = [
                collapse_whitespace(li.get_text(" "))
                for li in el.find_all("li")
                if collapse_whitespace(li.get_text())
            ]
            current_items.extend(items)

    if current_heading is not None and current_items:
        sections.append((current_heading, current_items))

    documents: list[Document] = []
    answers: list[PreparedAnswer] = []

    # Her bölüm için ayrı belge
    for heading, items in sections:
        slug, title, questions = _SECTIONS_META[heading]
        section_text = f"{title}\n\n" + "\n".join(f"- {item}" for item in items)
        documents.append(_doc(source, slug, title, section_text))
        answers.append(_answer(source, questions, section_text))

    # Prosedür adımları belgesi (görselden türetilmiş)
    documents.append(_doc(source, "prosedur", "Yaz Stajı Prosedür Adımları", _PROSEDUR_ADIMLARI))
    answers.append(
        _answer(
            source,
            [
                "Yaz stajı prosedürü nasıl işler?",
                "Staj için hangi adımları izlemeliyim?",
                "Staj başvurusu nasıl yapılır?",
                "Yaz stajını nasıl tamamlarım?",
                "Staj süreci baştan sona nasıl ilerliyor?",
                "Staj yapmak için sırayla ne yapmam gerekiyor?",
            ],
            _PROSEDUR_ADIMLARI,
        )
    )

    return SourceContent(documents=documents, prepared_answers=answers)


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
