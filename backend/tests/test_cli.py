import argparse

import pytest

from atilim_assistant import cli
from atilim_assistant.domain import Source, SourceContent


def _source(source_id: str) -> Source:
    return Source(
        id=source_id,
        title=source_id,
        url=f"https://example.edu/{source_id}",
        unit="Test Bölümü",
        category="test",
        parser=lambda html, source: SourceContent(documents=[], prepared_answers=[]),
    )


def test_ingest_skips_a_broken_source_and_reports_it(monkeypatch, capsys):
    monkeypatch.setattr(cli, "SOURCES", (_source("bozuk"), _source("saglam")))

    def load_content(source, html=None):
        if source.id == "bozuk":
            raise ValueError("sayfa yapısı değişmiş")
        return source.parser("", source)

    monkeypatch.setattr(cli, "load_content", load_content)

    with pytest.raises(SystemExit) as exit_info:
        cli._ingest(argparse.Namespace(source=None, html=None, dry_run=True))

    output = capsys.readouterr().out
    assert "bozuk: HATA — sayfa yapısı değişmiş" in output
    # Bozuk kaynaktan sonraki kaynak yine işlenir.
    assert "saglam: 0 belge" in output
    # Hata çıkış koduyla bildirilir: betikler ve CI fark eder.
    assert "bozuk" in str(exit_info.value)


def test_ingest_succeeds_when_every_source_works(monkeypatch, capsys):
    monkeypatch.setattr(cli, "SOURCES", (_source("saglam"),))
    monkeypatch.setattr(cli, "load_content", lambda source, html=None: source.parser("", source))

    cli._ingest(argparse.Namespace(source=None, html=None, dry_run=True))

    assert "saglam: 0 belge" in capsys.readouterr().out
