"""Yapılandırılmış veri kataloğu: dersler, bölüm kadrosu ve üniversitenin ders programı.

Sayfa metinleri belge olarak aranır; ama "hangi hocalar MATH dersi veriyor?" gibi sorular
birkaç metin parçasına sığmaz, cevabın tüm kayıtlar üzerinde hesaplanması gerekir. Ingest,
ayrıştırıcıların döndürdüğü kayıtları (`SourceContent.records`) ve ders programını bu
dosyaya yazar; sohbet sırasında model katalog araçlarıyla (`chat/tools.py`) sorgular.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from atilim_assistant.domain import Citation
from atilim_assistant.ingestion.parsers.departments.software_engineering.ders_programi import (
    Section,
    Timetable,
)

# Ders programı kayıtlarının anahtarı; diğer anahtarlar ayrıştırıcılardan gelir.
SECTIONS = "sections"


@dataclass(frozen=True, slots=True)
class Catalog:
    """Açılışta okunan, çalışırken değişmeyen katalog; `chat/tools.py`'deki araçlar sorgular.

    Kayıtlar sınıf değil sözlük olarak tutulur: alanları ayrıştırıcı belirler ve yeni bir alan
    eklemek yalnızca ayrıştırıcıyla onu okuyan aracı değiştirmeyi gerektirir.
    """

    # Bölüm müfredatındaki dersler: kod, ad, kategori, kredi, AKTS, ön koşul, içerik.
    courses: list[dict]
    # Akademik kadro: ad, görev, iletişim, eğitim, araştırma konuları.
    staff: list[dict]
    # Güncel dönemin ders programı (tüm üniversite, EduPage).
    timetable: Timetable
    # Kayıt türü → alındığı sayfa; araç sonuçlarında kaynak olarak gösterilir.
    sources: dict[str, Citation]
    # İdari personel (bölüm sekreteri vb.): ad, unvan, telefon, e-posta.
    admin_staff: list[dict] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "Catalog":
        """Kaydı olmayan katalog; katalog gerektirmeyen testler için."""
        return cls([], [], Timetable(term="", sections=()), {})


class CatalogStore:
    """Kayıt türü başına bir bölüm tutan tek bir JSON dosyası:
    {"courses": {"title": …, "url": …, "rows": […]}, "sections": {…, "term": …}}.

    Veritabanı yerine dosya kullanılır: katalog yalnızca ingest'te yazılır, sohbette yalnızca
    okunur ve küçüktür. Kaynak sayfası her kayıt türünün yanında saklanır ki yanıtın kaynağı
    gösterilebilsin.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def replace(self, key: str, rows: list[dict], citation: Citation, **extra: str) -> None:
        """Bir kayıt türünü yenileriyle değiştirir; diğer türlere dokunmaz.

        Dosya okunup yeniden yazılır, çünkü her kaynak yalnızca kendi türünü bilir: ders
        sayfasının ingest'i kadroyu silmemelidir. `extra`: türe özgü ek alanlar (ör. `term`).
        """
        data = self._read()
        data[key] = {"title": citation.title, "url": citation.url, "rows": rows, **extra}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def replace_timetable(self, timetable: Timetable, citation: Citation) -> None:
        """Ders programını yazar. Program bir sayfa ayrıştırıcısından değil, `cli ingest`
        içinde EduPage'den ayrıca çekildiği için kendi yöntemi vardır; dönemi de saklar."""
        rows = [asdict(section) for section in timetable.sections]
        self.replace(SECTIONS, rows, citation, term=timetable.term)

    def load(self) -> Catalog:
        """Kataloğu okur. Eksik kayıt türü boş liste olur: ingest'te alınamayan bir tür
        (ör. ders programı) uygulamayı durdurmaz, yalnızca ilgili araç sonuç vermez."""
        data = self._read()
        sections = data.get(SECTIONS, {})
        timetable = Timetable(
            term=sections.get("term", ""),
            sections=tuple(
                Section(row["code"], row["number"], row["name"], tuple(row["teachers"]))
                for row in sections.get("rows", [])
            ),
        )
        return Catalog(
            courses=data.get("courses", {}).get("rows", []),
            staff=data.get("staff", {}).get("rows", []),
            admin_staff=data.get("admin_staff", {}).get("rows", []),
            timetable=timetable,
            sources={
                key: Citation(title=entry["title"], url=entry["url"]) for key, entry in data.items()
            },
        )

    def _read(self) -> dict:
        """Dosya içeriği; ilk ingest'ten önce dosya yoktur ve boş katalog sayılır."""
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))
