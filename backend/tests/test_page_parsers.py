import pytest

from atilim_assistant.domain import Source
from atilim_assistant.ingestion.parsers.departments.software_engineering import (
    department_intro,
    dilekce_ornekleri,
    mufredat,
    yaz_stajlari,
)
from atilim_assistant.ingestion.parsers.university import iletisim

_EMPTY_PAGE = '<div class="detail-container"><div class="col-md-12"><p>Sayfa taşındı.</p></div></div>'


def _source(parser) -> Source:
    return Source(
        id="test-kaynak",
        title="Test Bölümü — Sayfa",
        url="https://example.edu/sayfa",
        unit="Test Bölümü",
        category="test",
        parser=parser,
    )


@pytest.mark.parametrize("parser", [yaz_stajlari.parse, dilekce_ornekleri.parse])
def test_parser_rejects_a_page_without_its_content(parser):
    # Boş içerik indekslenirse kaynağın eski ve doğru verisi silinirdi.
    with pytest.raises(ValueError):
        parser(_EMPTY_PAGE, _source(parser))


def test_internship_parser_reads_known_sections():
    html = """
    <div class="detail-container"><div class="col-md-12">
      <p>STAJ BAŞVURUSU İÇİN GEREKLİ BELGELER</p>
      <ol><li>Staj kabul belgesi</li></ol>
    </div></div>
    """
    content = yaz_stajlari.parse(html, _source(yaz_stajlari.parse))
    assert any("Staj kabul belgesi" in document.text for document in content.documents)


def test_petition_parser_reads_download_links():
    html = """
    <div class="detail-container">
      <a href="https://example.edu/kayit.docx">Kayıt Dondurma Dilekçesi</a>
    </div>
    """
    content = dilekce_ornekleri.parse(html, _source(dilekce_ornekleri.parse))
    assert any("kayit.docx" in document.text for document in content.documents)


_INTRO = (
    "Bölümümüz 2005 yılında kurulmuştur. "
    "Bölümümüz MÜDEK tarafından 30 Eylül 2030 tarihine kadar akredite edilmiştir. "
    "Bu etiket sayesinde mezunlarımız Avrupa'da avantaj sahibidir. "
    "Bölümümüz mezunları bankalarda ve Teknoparklarda çalışmaktadır. "
    "Bölüm Lisans, Yüksek Lisans ve Doktora düzeyinde eğitim verir."
)


def _intro_page(text: str) -> str:
    return f'<section class="site_landing_container"><p>{text}</p></section>'


def _answer_for(content, question: str) -> str | None:
    return next((a.answer for a in content.prepared_answers if question in a.questions), None)


def test_intro_answers_come_from_the_page():
    content = department_intro.parse(_intro_page(_INTRO), _source(department_intro.parse))

    accreditation = _answer_for(content, "Bölüm akredite mi?")
    assert accreditation == (
        "Bölümümüz MÜDEK tarafından 30 Eylül 2030 tarihine kadar akredite edilmiştir. "
        "Bu etiket sayesinde mezunlarımız Avrupa'da avantaj sahibidir."
    )
    # "mezunlarımız" geçen akreditasyon cümlesi iş olanakları yanıtına karışmaz.
    assert _answer_for(content, "Mezun iş imkânları neler?") == (
        "Bölümümüz mezunları bankalarda ve Teknoparklarda çalışmaktadır."
    )
    assert "Doktora düzeyinde" in _answer_for(content, "Doktora programı var mı?")


def test_intro_answer_is_skipped_when_the_page_no_longer_says_it():
    # Sayfada artık akreditasyon cümlesi yoksa eskimiş bir yanıt verilmez; soru modele gider.
    content = department_intro.parse(
        _intro_page("Bölümümüz 2005 yılında kurulmuştur."), _source(department_intro.parse)
    )
    assert _answer_for(content, "Bölüm akredite mi?") is None
    assert _answer_for(content, "Mezun iş imkânları neler?") is None
    assert _answer_for(content, "Doktora programı var mı?") is None


def _curriculum_page() -> str:
    def row(code: str, akts: int) -> str:
        data = f'{{"code": "{code}", "name": "Ders {code}", "theory": 3, "practice": 0, "akts": {akts}}}'
        return f"<tr><td><a class='lesson_card' data-lesson-data='{data}'>{code}</a></td></tr>"

    semesters = "".join(
        f"<h3>{n}. Yarıyıl</h3><table>{row(f'SE{n}01', 6)}"
        f"<tr><td>Toplam</td><td>3</td><td>0</td><td>30</td></tr></table>"
        for n in range(5, 7)
    )
    return f'<div class="detail-container">{semesters}</div>'


def test_curriculum_tables_are_not_swallowed_by_numbered_headings():
    """"5. Yarıyıl" ile başlayan satır Markdown'da numaralı liste maddesidir; hemen altındaki
    tablo o maddenin düz metnine dönüşür. Tablodan önceki satır rakam ve noktayla başlamamalı."""
    content = mufredat.parse(_curriculum_page(), _source(mufredat.parse))
    answer = _answer_for(content, "3. sınıf dersleri neler?")
    assert "| SE501 | Ders SE501 | 6 |" in answer
    lines = answer.splitlines()
    for before, line in zip(lines, lines[1:]):
        if line.startswith("| Kod |"):
            assert not before[:1].isdigit(), before


def test_contact_parser_reads_address_and_adds_map():
    html = """
    <div class="detail-container">
      <h2>Atılım Üniversitesi - İncek Yerleşkesi</h2>
      <p><strong>Adres</strong>: Kızılcaşar Mahallesi, 06830 İncek</p>
      <p><strong>Telefon</strong>: +90 (312) 586 80 00</p>
      <p><strong>Rektörlük</strong><br />atiliminfo@atilim.edu.tr</p>
    </div>
    """
    content = iletisim.parse(html, _source(iletisim.parse))
    location, contact = content.prepared_answers
    assert "06830 İncek" in location.answer and iletisim.MAP_EMBED_URL in location.answer
    assert "586 80 00" in contact.answer and "atiliminfo@atilim.edu.tr" in contact.answer


def test_contact_parser_rejects_a_page_without_address():
    with pytest.raises(ValueError):
        iletisim.parse(_EMPTY_PAGE, _source(iletisim.parse))
