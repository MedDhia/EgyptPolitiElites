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


def _cmd_origin(args: argparse.Namespace) -> int:
    """Positional advantage by community of origin, across the waves."""
    import warnings

    from .figures_journal import build_all
    from .positional import build_panel, by_wave, concentration, permutation_test
    from .viz import figure_positional

    processed = Path(args.processed) if args.processed else config.PROCESSED
    if not (processed / "affiliations.csv").exists():
        print(f"no dataset at {processed}. Run `politi build --roster` first.",
              file=sys.stderr)
        return 1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        panel = build_panel(processed)
        panel.to_csv(processed / "origin_panel.csv", index=False)
        by_wave(panel).to_csv(processed / "origin_coefficients_by_wave.csv", index=False)
        permutation_test(panel, n_perm=args.permutations).to_csv(
            processed / "origin_permutation.csv", index=False)
        concentration(panel).to_csv(processed / "origin_concentration.csv", index=False)
        fig = figure_positional(panel, (config.ROOT / "figures" /
                                        "positional_advantage.png"))
        journal = build_all(panel, config.ROOT / "figures" / "journal",
                            n_perm=args.permutations)
    counts = panel.groupby("origin", observed=True).size()
    for grp, n in counts.items():
        print(f"  {grp:<16} {n:,} person-wave observations")
    print(f"\nwrote 4 tables to {processed}")
    print(f"wrote {fig}")
    print(f"wrote {len(journal)} journal figures to "
          f"{config.ROOT / 'figures' / 'journal'}")
    return 0


def _cmd_figures(args: argparse.Namespace) -> int:
    """Render the network figures from the built dataset."""
    from .viz import build_figures

    processed = Path(args.processed) if args.processed else config.PROCESSED
    if not (processed / "affiliations.csv").exists():
        print(f"no dataset at {processed}. Run `politi build --roster` first.",
              file=sys.stderr)
        return 1
    for path in build_figures(processed, Path(args.out) if args.out else None):
        print(f"wrote {path}")
    return 0


def _cmd_explore(args: argparse.Namespace) -> int:
    """Render the descriptive figures, one file each."""
    from .explore import build_all

    processed = Path(args.processed) if args.processed else config.PROCESSED
    if not (processed / "affiliations.csv").exists():
        print(f"no dataset at {processed}. Run `politi build --roster` first.",
              file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else config.ROOT / "figures" / "explore"
    if not (processed / "origin_panel.csv").exists():
        print("no origin_panel.csv: skipping the two figures that need imputed "
              "origin. Run `politi origin` to produce it.", file=sys.stderr)
    for path in build_all(processed, out):
        print(f"wrote {path}")
    return 0


def _cmd_tergm(args: argparse.Namespace) -> int:
    """Export the network panel a temporal ERGM is fitted to."""
    from .tergm import export_for_r, network_panel, transition_table

    processed = Path(args.processed) if args.processed else config.PROCESSED
    if not (processed / "affiliations.csv").exists():
        print(f"no dataset at {processed}. Run `politi build --roster` first.",
              file=sys.stderr)
        return 1
    panel = network_panel(processed, drop_1932=args.from_1938)
    table = transition_table(panel)
    print(table.to_string(index=False))
    print("\nThe model is estimated on dyads whose both endpoints appear in "
          "consecutive waves.\nSee docs/TERGM.md before reading any "
          "coefficient.")
    # --from-1938 is a different panel and must not overwrite the other:
    # the R script reads whatever is in the directory, and would label a
    # 1938-only fit as the full series.
    default = processed / ("tergm_from1938" if args.from_1938 else "tergm")
    out = Path(args.out) if args.out else default
    for path in export_for_r(panel, out):
        print(f"wrote {path}")

    if args.fit:
        from .tergm import change_statistics, fit_mple

        design = change_statistics(panel)
        print(f"\nfitting on {len(design):,} at-risk dyads, "
              f"{int(design.tie.sum())} ties "
              f"({args.bootstrap} bootstrap replications)")
        table = fit_mple(design, n_boot=args.bootstrap)
        print(table.round(3).to_string(index=False))
        tag = "_from1938" if args.from_1938 else ""
        path = processed / f"tergm_mple{tag}.csv"
        table.to_csv(path, index=False)
        print(f"\nwrote {path}")
    else:
        print("\nNow: Rscript scripts/tergm.R, or --fit for the "
              "pseudolikelihood fit in Python")
    return 0



def _cmd_holes(args: argparse.Namespace) -> int:
    """Embeddedness against structural holes, in both halves."""
    import pandas as pd

    from .holes import (brokerage_panel, brokerage_regression, closure_design,
                        closure_stratified, distance_table, fit_baseline,
                        fit_closure, returns_to_brokerage)
    from .tergm import network_panel

    processed = Path(args.processed) if args.processed else config.PROCESSED
    if not (processed / "affiliations.csv").exists():
        print(f"no dataset at {processed}. Run `politi build --roster` first.",
              file=sys.stderr)
        return 1
    panel = network_panel(processed, drop_1932=args.from_1938)

    print("=== formation: does a prior board-mate on the board predict "
          "joining it? ===\n")
    design = closure_design(panel)
    print(distance_table(design).round(3).to_string(index=False))
    baseline = fit_baseline(design, n_boot=args.bootstrap)
    print("\n-- no closure term, for comparison --")
    print(baseline.round(3).to_string(index=False))
    forms = [baseline]
    for form in ("closure", "closure_any", "closure_log", "closure4"):
        table = fit_closure(design, closure=form, n_boot=args.bootstrap)
        forms.append(table)
        print(f"\n-- {form} --")
        print(table.round(3).to_string(index=False))
    fits = pd.concat(forms, ignore_index=True)

    print("\n-- within wave x board-mates x board-size cells, "
          "with a within-cell permutation null --")
    strat = closure_stratified(design, n_perm=args.permutations)
    for key, value in strat.items():
        print(f"   {key:14s} {value}")

    print("\n=== returns: do brokers gain seats and survive more than "
          "directors of the same size? ===\n")
    broker = brokerage_panel(panel)
    returns = pd.concat([returns_to_brokerage(broker, outcome=o)
                         for o in ("new_seats", "survives", "growth")],
                        ignore_index=True)
    print(returns.round(3).to_string(index=False))
    print("\n-- the same question with contact volume held fixed, which is "
          "the test Burt's claim actually needs --")
    regression = brokerage_regression(broker)
    print(regression.round(3).to_string(index=False))

    tag = "_from1938" if args.from_1938 else ""
    written = {
        f"closure_fits{tag}.csv": fits,
        f"closure_distance{tag}.csv": distance_table(design),
        f"closure_stratified{tag}.csv": pd.DataFrame([strat]),
        f"brokerage_returns{tag}.csv": returns,
        f"brokerage_regression{tag}.csv": regression,
        f"brokerage_panel{tag}.csv": broker,
    }
    for name, frame in written.items():
        frame.to_csv(processed / name, index=False)
        print(f"wrote {processed / name}")

    from .holes_viz import fig_brokerage, fig_closure

    figures = Path(args.figures) if args.figures else config.ROOT / "figures" / "holes"
    for path in (fig_closure(distance_table(design), fits, strat,
                             figures / f"closure{tag}.png"),
                 fig_brokerage(regression, figures / f"brokerage{tag}.png")):
        print(f"wrote {path}")
    print("\nSee docs/EMBEDDEDNESS.md before reading any of it.")
    return 0


def _cmd_politics(args: argparse.Namespace) -> int:
    """Render the political-connection figures, one file each."""
    from .politics_viz import build_all

    processed = Path(args.processed) if args.processed else config.PROCESSED
    missing = [f for f in ("affiliations.csv", "person_political.csv",
                           "firm_political.csv", "military_officers.csv")
               if not (processed / f).exists()]
    if missing:
        print(f"missing {', '.join(missing)} in {processed}. "
              "Run `politi build --roster` first.", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else config.ROOT / "figures" / "politics"
    for path in build_all(processed, out):
        print(f"wrote {path}")
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

    f = sub.add_parser("figures", help="render the network figures")
    f.add_argument("--processed", help="dataset directory (default data/processed)")
    f.add_argument("--out", help="output directory (default figures/)")
    f.set_defaults(func=_cmd_figures)

    x = sub.add_parser("explore",
                       help="render the descriptive figures, one file each")
    x.add_argument("--processed", help="dataset directory (default data/processed)")
    x.add_argument("--out", help="output directory (default figures/explore/)")
    x.set_defaults(func=_cmd_explore)

    pol = sub.add_parser("politics",
                         help="render the political-connection figures")
    pol.add_argument("--processed", help="dataset directory (default data/processed)")
    pol.add_argument("--out", help="output directory (default figures/politics/)")
    pol.set_defaults(func=_cmd_politics)

    tg = sub.add_parser("tergm",
                        help="export the network panel for the temporal ERGM")
    tg.add_argument("--processed", help="dataset directory (default data/processed)")
    tg.add_argument("--out", help="output directory (default <processed>/tergm)")
    tg.add_argument("--from-1938", dest="from_1938", action="store_true",
                    help="drop 1932, whose roster is a selection")
    tg.add_argument("--fit", action="store_true",
                    help="also fit by pseudolikelihood with a node bootstrap")
    tg.add_argument("--bootstrap", type=int, default=200,
                    help="bootstrap replications for --fit (default 200)")
    tg.set_defaults(func=_cmd_tergm)

    hl = sub.add_parser("holes",
                        help="embeddedness against structural holes")
    hl.add_argument("--processed", help="dataset directory (default data/processed)")
    hl.add_argument("--from-1938", dest="from_1938", action="store_true",
                    help="drop 1932, whose roster is a selection")
    hl.add_argument("--bootstrap", type=int, default=100,
                    help="bootstrap replications for the formation fit")
    hl.add_argument("--permutations", type=int, default=2000)
    hl.add_argument("--figures", help="figure directory (default figures/holes/)")
    hl.set_defaults(func=_cmd_holes)

    o = sub.add_parser("origin",
                       help="positional advantage by community of origin")
    o.add_argument("--processed", help="dataset directory (default data/processed)")
    o.add_argument("--permutations", type=int, default=20000)
    o.set_defaults(func=_cmd_origin)

    args = ap.parse_args(argv)
    return args.func(args)
