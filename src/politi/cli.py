"""Command line entry point: ``python -m politi <command>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config


def _cmd_sources(args: argparse.Namespace) -> int:
    print(f"{'year':<6}{'ed.':<6}{'place':<12}{'on disk':<20}source")
    for y in config.WAVES:
        ed = config.edition(y)
        num = f"{ed.edition}{'' if ed.edition_verified else '?'}"
        sources = ed.pdf_sources()
        if sources:
            have = f"yes ({len(sources)} file{'s' if len(sources) > 1 else ''})"
        elif ed.text_path.exists():
            have = "yes (text)"
        else:
            have = "no"
        print(f"{y:<6}{num:<6}{ed.place:<12}{have:<20}{ed.url or ed.note}")
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
        sources = ed.pdf_sources()
        force = args.force_ocr or ed.bad_text_layer
        how = " (re-OCR)" if force else ""
        print(f"[{y}] extracting {', '.join(p.name for p in sources)}{how}")
        text = extract_pdf(sources, ocr_fallback=not args.no_ocr, force_ocr=force)
        ed.text_path.parent.mkdir(parents=True, exist_ok=True)
        ed.text_path.write_text(text, encoding="utf-8")
        print(f"[{y}] -> {ed.text_path} ({len(text):,} chars)")
    return 0


def _cmd_split(args: argparse.Namespace) -> int:
    """Split a volume into parts small enough to travel through a connector."""
    from .drive import split_pdf

    src = Path(args.pdf)
    if not src.exists():
        print(f"no such file: {src}", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else config.INCOMING
    stem = f"politi_{args.year}" if args.year else None
    parts = split_pdf(src, out, max_bytes=int(args.max_mb * 1024 * 1024), stem=stem)
    if parts == [src]:
        print(f"{src.name} is already under {args.max_mb} MB — no split needed")
        return 0
    for part in parts:
        print(f"{part}  ({part.stat().st_size / 1e6:.1f} MB)")
    print(f"\n{len(parts)} parts in {out}")
    return 0


def _cmd_drive_import(args: argparse.Namespace) -> int:
    """Land a saved download_file_content result into data/raw/."""
    from .drive import save_tool_result

    try:
        dest = save_tool_result(Path(args.result), args.year, part=args.part)
    except (ValueError, OSError) as exc:
        print(f"import failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    from .build import (build_from_rosters, build_tables, parse_available,
                        parse_rosters)
    from .export import export_all
    from .parse import parse_volume

    outdir = Path(args.out) if args.out else config.PROCESSED

    if args.roster:
        # Build from the volume's biographical roster of directors, which is
        # person-side and needs no within-volume person resolution.
        rosters = parse_rosters([args.year] if args.year else None)
        if not rosters:
            print("no biographical roster found. `python -m politi sources` shows "
                  "what is on disk; docs/SOURCES.md says where to get it.",
                  file=sys.stderr)
            return 1
        for y, bios in sorted(rosters.items()):
            n = sum(len(b.positions) for b in bios)
            print(f"[{y}] {len(bios):,} directors, {n:,} printed positions")
        tables = build_from_rosters(rosters, firms_only=not args.include_bodies)
        written = export_all(tables, outdir)
        print(f"\npersons        {len(tables['persons']):,}")
        print(f"companies      {len(tables['companies']):,}")
        print(f"affiliations   {len(tables['affiliations']):,}")
        print(f"\nwrote {sum(len(v) for v in written.values())} files to {outdir}")
        return 0

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
    e.add_argument("--force-ocr", action="store_true",
                   help="ignore the embedded text layer and re-OCR every page")
    e.set_defaults(func=_cmd_extract)

    sp = sub.add_parser("split", help="split a volume into connector-sized parts")
    sp.add_argument("--pdf", required=True)
    sp.add_argument("--year", type=int, help="name parts politi_<year>_partNN.pdf")
    sp.add_argument("--out", help="output directory (default data/incoming)")
    sp.add_argument("--max-mb", type=float, default=9.0,
                    help="part size ceiling in MB (default 9, under the Drive cap)")
    sp.set_defaults(func=_cmd_split)

    di = sub.add_parser("drive-import",
                        help="land a saved download_file_content result in data/raw")
    di.add_argument("--result", required=True, help="path to the saved tool-result JSON")
    di.add_argument("--year", type=int, required=True)
    di.add_argument("--part", type=int, help="part number, if the volume was split")
    di.set_defaults(func=_cmd_drive_import)

    b = sub.add_parser("build", help="parse, resolve, and export the dataset")
    b.add_argument("--year", type=int)
    b.add_argument("--text", help="build from a single text file instead")
    b.add_argument("--out", help="output directory (default data/processed)")
    b.add_argument("--roster", action="store_true",
                   help="build from the biographical roster of directors")
    b.add_argument("--include-bodies", action="store_true",
                   help="keep councils, chambers and commissions alongside firms")
    b.set_defaults(func=_cmd_build)

    args = ap.parse_args(argv)
    return args.func(args)
