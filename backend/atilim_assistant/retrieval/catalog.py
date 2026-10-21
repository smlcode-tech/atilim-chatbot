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
    courses: list[dict]
    staff: list[dict]
    timetable: Timetable
    sources: dict[str, Citation]
    # İdari personel (bölüm sekreteri vb.): ad, unvan, telefon, e-posta.
    admin_staff: list[dict] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "Catalog":
        return cls([], [], Timetable(term="", sections=()), {})


class CatalogStore:
    """Kayıt türü başına bir bölüm tutan tek bir JSON dosyası:
    {"courses": {"title": …, "url": …, "rows": […]}, "sections": {…, "term": …}}."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def replace(self, key: str, rows: list[dict], citation: Citation, **extra: str) -> None:
        """Bir kayıt türünü yenileriyle değiştirir; diğer türlere dokunmaz."""
        data = self._read()
        data[key] = {"title": citation.title, "url": citation.url, "rows": rows, **extra}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def replace_timetable(self, timetable: Timetable, citation: Citation) -> None:
        rows = [asdict(section) for section in timetable.sections]
        self.replace(SECTIONS, rows, citation, term=timetable.term)

    def load(self) -> Catalog:
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
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))
