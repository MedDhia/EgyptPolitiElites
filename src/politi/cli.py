"""Command line entry point: ``python -m politi <command>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config


def _cmd_sources(args: argparse.Namespace) -> int:
    print(f"{'year':<6}{'ed.':<6}{'place':<12}{'pdf on disk':<13}source")
    for y in config.WAVES:
        ed = config.edition(y)
        num = f"{ed.edition}{'' if ed.edition_verified else '?'}"
        have = "yes" if ed.pdf_path.exists() else "no"
        print(f"{y:<6}{num:<6}{ed.place:<12}{have:<13}{ed.url or ed.note}")
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    from .fetch import fetch_all, fetch_wave

    if args.year:
        fetch_wave(args.year, force=args.force)
    else:
        fetch_all(force=args.force)
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    from .pdftext import extract_pdf

    years = [args.year] if args.year else config.available_waves()
    if not years:
        print("no PDFs in data/raw — run `fetch` first", file=sys.stderr)
        return 1
    for y in years:
        ed = config.edition(y)
        print(f"[{y}] extracting {ed.pdf_path.name}")
        text = extract_pdf(ed.pdf_path, ocr_fallback=not args.no_ocr)
        ed.text_path.parent.mkdir(parents=True, exist_ok=True)
        ed.text_path.write_text(text, encoding="utf-8")
        print(f"[{y}] -> {ed.text_path} ({len(text):,} chars)")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    from .build import build_tables, parse_available
    from .export import export_all
    from .parse import parse_volume

    outdir = Path(args.out) if args.out else config.PROCESSED

    if args.text:
        # Build straight from a text file, bypassing the source registry.
        src = Path(args.text)
        if not src.exists():
            print(f"no such file: {src}", file=sys.stderr)
            return 1
        year = args.year or 0
        volumes = {year: parse_volume(src.read_text(encoding="utf-8"))}
    else:
        volumes = parse_available([args.year] if args.year else None)

    if not volumes:
        print("no parsable volumes found. `python -m politi sources` shows what is "
              "missing; docs/SOURCES.md says where to get it.", file=sys.stderr)
        return 1

    for y, comps in sorted(volumes.items()):
        n_ties = sum(len(c.directorships) for c in comps)
        print(f"[{y}] {len(comps):,} companies, {n_ties:,} printed directorships")

    tables = build_tables(volumes)
    written = export_all(tables, outdir)
    print(f"\npersons        {len(tables['persons']):,}")
    print(f"companies      {len(tables['companies']):,}")
    print(f"affiliations   {len(tables['affiliations']):,}")
    print(f"\nwrote {sum(len(v) for v in written.values())} files to {outdir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="politi", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="show each wave and whether it is on disk"
                   ).set_defaults(func=_cmd_sources)

    f = sub.add_parser("fetch", help="download the annuaire PDFs")
    f.add_argument("--year", type=int, choices=config.WAVES)
    f.add_argument("--force", action="store_true")
    f.set_defaults(func=_cmd_fetch)

    e = sub.add_parser("extract", help="PDF -> text")
    e.add_argument("--year", type=int, choices=config.WAVES)
    e.add_argument("--no-ocr", action="store_true", help="skip the OCR fallback")
    e.set_defaults(func=_cmd_extract)

    b = sub.add_parser("build", help="parse, resolve, and export the dataset")
    b.add_argument("--year", type=int)
    b.add_argument("--text", help="build from a single text file instead")
    b.add_argument("--out", help="output directory (default data/processed)")
    b.set_defaults(func=_cmd_build)

    args = ap.parse_args(argv)
    return args.func(args)
