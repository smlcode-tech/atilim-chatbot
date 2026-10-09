import json
import re
import sys

import requests
from bs4 import BeautifulSoup, NavigableString

URL = "https://www.atilim.edu.tr/tr/se/page/2286/akademik-personel"
UNVANLAR = r"(Prof\. Dr\.|Doç\. Dr\.|Dr\. Öğr\. Üyesi|Öğr\. Gör\. Dr\.|Öğr\. Gör\.|Arş\. Gör\.)"

# Kullanım: python scrape.py            -> siteden çeker
#           python scrape.py sayfa.html -> yerel HTML dosyasından okur (hata ayıklama için)
if len(sys.argv) > 1:
    html_text = open(sys.argv[1], encoding="utf-8").read()
else:
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.encoding = "utf-8"
    html_text = resp.text

soup = BeautifulSoup(html_text, "html.parser")


def blok_metni(baslik):
    """Bir h4'ten sonraki ilk h2/h3/h4'e kadar olan tüm metni toplar."""
    parcalar = []
    for el in baslik.next_elements:
        if getattr(el, "name", None) in ("h2", "h3", "h4"):
            break
        if isinstance(el, NavigableString):
            t = el.strip()
            if t:
                parcalar.append(t)
    metin = " ".join(parcalar)
    return metin.split("Kızılcaşar")[0]  # son kişiye footer karışmasın


kisiler = []
for h in soup.find_all("h4"):
    baslik = h.get_text(" ", strip=True)
    m = re.match(UNVANLAR + r"\s+(.+)", baslik.split(" / ")[0])
    if not m:
        continue
    unvan, ad = m.group(1), m.group(2).strip()
    gorev = baslik.split(" / ")[1] if " / " in baslik else ""

    metin = blok_metni(h)
    tel = re.search(r"\+90 \(312\) [\d ]+", metin)
    arastirma = re.search(r"Araştırma Konuları\s*:\s*(.+)", metin)
    egitim = re.search(r"(Lisans.*?)(?:Araştırma Konuları|$)", metin)

    kisiler.append({
        "unvan": unvan,
        "ad": ad,
        "gorev": gorev,
        "telefon": tel.group(0).strip() if tel else "",
        "egitim": egitim.group(1).strip() if egitim else "",
        "arastirma_konulari": arastirma.group(1).strip() if arastirma else "",
    })

for k in kisiler:
    parcalar = [f"Ad: {k['unvan']} {k['ad']}"]
    if k["gorev"]:
        parcalar.append(f"Görev: {k['gorev']}")
    if k["telefon"]:
        parcalar.append(f"Telefon: {k['telefon']}")
    if k["egitim"]:
        parcalar.append(f"Eğitim: {k['egitim']}")
    parcalar.append(
        f"Araştırma Konuları: {k['arastirma_konulari'] or 'Sayfada belirtilmemiş'}"
    )
    k["metin"] = "\n".join(parcalar)

with open("people.json", "w", encoding="utf-8") as f:
    json.dump(kisiler, f, ensure_ascii=False, indent=2)

print(f"{len(kisiler)} kişi kaydedildi")
for k in kisiler:
    print("-", k["unvan"], k["ad"])
