"""Command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import requests

from . import __version__
from .scraper import audit, fetch_epub, probe, scrape


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="novel-pipeline",
        description="Bölüm metni ve görselleri indirip EPUB üretir.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("probe", "Tek sayfayı incele"),
        ("fetch", "Bölümleri sırayla indir"),
    ):
        cmd = commands.add_parser(name, help=help_text)
        cmd.add_argument("--url", required=True)
        cmd.add_argument("--content-selector")
        cmd.add_argument("--next-selector")
        cmd.add_argument("--min-chars", type=int, default=200)
        cmd.add_argument("--browser", action="store_true",
                         help="JavaScript sayfaları için Selenium/Chromium")
        cmd.add_argument("--headless", action="store_true",
                         help="--browser ile ekransız çalıştır")
        if name == "fetch":
            cmd.add_argument("--slug", required=True)
            cmd.add_argument("--max-chapters", type=int, default=1,
                             help="0 = sonraki bağlantı kalmayıncaya kadar")
            cmd.add_argument("--delay", type=float, default=2.5,
                             help="İstekler arası bekleme (saniye)")
            cmd.add_argument("--images", action="store_true")
            cmd.add_argument("--output", default="output")

    cmd = commands.add_parser("epub", help="İndirilen bölümlerden EPUB üret")
    cmd.add_argument("--slug", required=True)
    cmd.add_argument("--output", default="output")
    cmd.add_argument("--title", default="")
    cmd.add_argument("--author", default="")
    cmd.add_argument("--lang", default="en")

    cmd = commands.add_parser("audit", help="Bölümleri ve HTTP raporunu kontrol et")
    cmd.add_argument("--slug", required=True)
    cmd.add_argument("--output", default="output")
    cmd.add_argument("--expected", type=int, default=0,
                     help="Beklenen en az bölüm sayısı")
    cmd.add_argument("--min-chars", type=int, default=200,
                     help="Bir bölümün kabul edilen en düşük uzunluğu")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "headless", False) and not getattr(args, "browser", False):
        parser.error("--headless yalnız --browser ile kullanılabilir")

    try:
        if args.command == "probe":
            return probe(args)
        if args.command == "fetch":
            return scrape(args)
        if args.command == "epub":
            return fetch_epub(args)
        return audit(Path(args.output), args.slug, args.expected, args.min_chars)
    except (ValueError, OSError, requests.RequestException) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
