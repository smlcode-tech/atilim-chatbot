"""Personel kartlarındaki resim olarak yayınlanmış e-posta adreslerini çözer.

Personel sayfalarında e-posta adresi metin değil, base64 gömülü PNG resim olarak yayınlanır
(bot koruması). Resimler bir kez okunup `data/personel_eposta.json` dosyasına, resmin SHA-256
özeti anahtar olacak biçimde kaydedilmiştir. Anahtar isim değil resimdir: isim yazımı değişse
de eşleşme bozulmaz; adres değişirse resim de değişir, eski adres verilmez. Bilinmeyen bir resim
görülürse ingest uyarı verir; uyarıdaki özetle resmi okuyup dosyaya eklemek yeter.
"""

import hashlib
import json
import logging
from pathlib import Path

from bs4 import Tag

# Resim sayfaya gömülü gelir (`src="data:image/png;base64,…"`); özet bu önekten sonrası üzerinden alınır.
_IMAGE_PREFIX = "data:image/png;base64,"
EMAILS_PATH = Path(__file__).parent / "data" / "personel_eposta.json"

logger = logging.getLogger(__name__)


def known_emails() -> dict[str, str]:
    """E-posta resminin SHA-256 özeti → adres. Dosyada ad da tutulur (okunurluk için),
    eşleştirmede kullanılmaz."""
    entries = json.loads(EMAILS_PATH.read_text(encoding="utf-8"))
    return {digest: entry["email"] for digest, entry in entries.items()}


def card_email(card: Tag, name: str, emails: dict[str, str]) -> str:
    """Karttaki zarf simgesinin yanındaki resmin adresi; resim yoksa ya da tanınmıyorsa boş.

    Tanınmayan resimde ingest durmaz, yalnızca uyarır: tek kişinin e-postası eksik kalır, yanıt
    da kullanıcıyı kaynak sayfaya yönlendirir. Yanlış bir adres vermektense boş bırakılır.
    """
    envelope = card.select_one("i.fa-envelope-o")
    image = envelope.find_next_sibling("img") if envelope else None
    source = image.get("src", "") if image else ""
    if not source.startswith(_IMAGE_PREFIX):
        return ""
    digest = hashlib.sha256(source.removeprefix(_IMAGE_PREFIX).encode()).hexdigest()
    if digest not in emails:
        logger.warning(
            "%s için e-posta resmi tanınmıyor (özet %s). Resmi okuyup %s dosyasına ekle.",
            name,
            digest,
            EMAILS_PATH.name,
        )
        return ""
    return emails[digest]
