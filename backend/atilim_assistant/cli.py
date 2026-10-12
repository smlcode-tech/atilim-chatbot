"""Komut satırı arayüzü: ingest (indeksle), serve (API), chat (terminalde sohbet)."""

import argparse
import logging
from pathlib import Path

import uvicorn

from atilim_assistant.bootstrap import (
    build_chat_service,
    build_prepared_answer_store,
    build_provider,
    build_store,
)
from atilim_assistant.config import get_settings
from atilim_assistant.ingestion.pipeline import index_content, load_content
from atilim_assistant.ingestion.sources import SOURCES, get_source


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m atilim_assistant", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Kaynak sayfaları çekip indeksler.")
    ingest.add_argument("--source", help="Yalnızca bu kimlikteki kaynağı işle.")
    ingest.add_argument(
        "--html", type=Path, help="Sayfayı siteden çekmek yerine bu dosyadan oku (--source ile)."
    )
    ingest.add_argument(
        "--dry-run",
        action="store_true",
        help="İndekslemeden, üretilen belgeleri ve hazır yanıtları yazdır.",
    )
    ingest.set_defaults(run=_ingest)

    commands.add_parser("serve", help="HTTP API'yi başlatır.").set_defaults(run=_serve)
    commands.add_parser("chat", help="Terminalde sohbet başlatır.").set_defaults(run=_chat)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    args.run(args)


def _ingest(args: argparse.Namespace) -> None:
    if args.html and not args.source:
        raise SystemExit("--html yalnızca --source ile birlikte kullanılabilir.")
    sources = [get_source(args.source)] if args.source else list(SOURCES)
    html = args.html.read_text(encoding="utf-8") if args.html else None

    if not args.dry_run:
        settings = get_settings()
        _chat_model, provider = build_provider(settings)
        store = build_store(settings)
        prepared_answers = build_prepared_answer_store(settings)

    for source in sources:
        content = load_content(source, html)
        if args.dry_run:
            for document in content.documents:
                print(f"\n=== {document.id} ===\n{document.text}")
            for prepared in content.prepared_answers:
                print(f"\n=== Hazır yanıt: {' | '.join(prepared.questions)} ===\n{prepared.answer}")
        else:
            index_content(source, content, provider, store, prepared_answers)
        print(
            f"{source.id}: {len(content.documents)} belge, "
            f"{len(content.prepared_answers)} hazır yanıt"
        )


def _serve(_: argparse.Namespace) -> None:
    settings = get_settings()
    uvicorn.run(
        "atilim_assistant.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
    )


def _chat(_: argparse.Namespace) -> None:
    service = build_chat_service(get_settings())
    while True:
        question = input("\nSoru (çıkış: q): ").strip()
        if question.lower() == "q":
            break
        if not question:
            continue
        answer = service.answer(question)
        if answer.prepared:
            print("(Hazır yanıt — yapay zekâ modeli şu anda yanıt üretemiyor.)")
        print(answer.text)
        for citation in answer.citations:
            print(f"  Kaynak: {citation.title} <{citation.url}>")
