import hashlib
import json

import pytest

from atilim_assistant.domain import Source
from atilim_assistant.ingestion.parsers.departments.software_engineering import (
    idari_personel,
    staff_emails,
)

_HTML = """
<div class="staff-academician clearfix">
  <h4>Deniz ÖRNEK<small> / Bölüm Sekreteri</small></h4>
  <p><i class="fa fa-envelope-o"></i> <img src="data:image/png;base64,BBBB" > /
     <i class="fa fa-phone"></i> +90 (312) 586 8398</p>
</div>
"""


@pytest.fixture
def source() -> Source:
    return Source(
        id="test-idari-personel",
        title="Test Bölümü — İdari Personel",
        url="https://example.edu/idari-personel",
        unit="Test Bölümü",
        category="idari-personel",
        parser=idari_personel.parse,
    )


def test_contact_answer_carries_phone_and_resolved_email(source, tmp_path, monkeypatch):
    path = tmp_path / "eposta.json"
    digest = hashlib.sha256(b"BBBB").hexdigest()
    path.write_text(json.dumps({digest: {"name": "Deniz", "email": "deniz@example.edu"}}))
    monkeypatch.setattr(staff_emails, "EMAILS_PATH", path)

    content = idari_personel.parse(_HTML, source)

    assert "E-posta: deniz@example.edu" in content.documents[1].text
    contact = next(a for a in content.prepared_answers if "Deniz ÖRNEK iletişim bilgileri" in a.questions)
    assert contact.answer == "**Deniz ÖRNEK** — telefon: +90 (312) 586 8398, e-posta: deniz@example.edu"
    assert content.records == {"admin_staff": [{
        "name": "Deniz ÖRNEK", "title": "Bölüm Sekreteri",
        "phone": "+90 (312) 586 8398", "email": "deniz@example.edu",
    }]}


def test_unknown_email_image_leaves_only_the_phone(source):
    content = idari_personel.parse(_HTML, source)

    contact = next(a for a in content.prepared_answers if "Deniz ÖRNEK iletişim bilgileri" in a.questions)
    assert contact.answer == "**Deniz ÖRNEK** — telefon: +90 (312) 586 8398"
