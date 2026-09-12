"""Firm sector, and the directors attached to it.

Unlike office and military rank, sector is not printed against a director. It
is a property of the *firms* he sits on, so a "financier" here is a director
recorded on at least one bank, insurance company, credit or mortgage house in
that wave — an attribute assembled from the network, not read off the page.

That difference creates an arithmetic trap, and every function below is shaped
around it. **Roughly one directorship in eight is on a financial firm, so a
director with five seats is far likelier to hold one than a director with one
seat, whatever else is true of him.** Comparing financiers with everyone else
therefore compares the many-seated with the few-seated, and will show a large
"finance effect" built entirely out of seat counts. The comparisons here are
made inside wave × seat-count cells for that reason, and `fin_share` — the
share of a director's own seats that are financial — is provided as the
measure that has no such arithmetic in it.

The coding is of the firm's *name*, which is what the annuaire gives. A bank
is named as one; a family holding company that lends is not.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from unidecode import unidecode

#: Banks, insurers, credit and mortgage houses. Deliberately narrow.
FINANCIAL = re.compile(
    r"(?i)\bbanque?s?\b|\bbank\b|\bbanca\b|\bbanco\b|\bcredit[oi]?\b|"
    r"\bassurances?\b|\breassurances?\b|\binsurance\b|\bassicurazioni\b|"
    r"\bfinanci[eè]re?s?\b|\bfinance\b|\bfinancial\b|"
    r"\bhypothecaire\b|\bmortgage\b|\bcaisse\b")

#: Public and professional bodies whose names carry a sector word — a ministry
#: of finance, a committee on reinsurance, a consultative council on
#: agriculture — and which are not firms.
NOT_A_FIRM = re.compile(
    r"(?i)\bminist[eè]re\b|\bcomit[eé]\b|\bcommission\b|"
    r"\bconseil\s+(?:sup|cons)|\bconsultatif\b|\bchambre\b|\bsyndicat\b|"
    r"\bassociation\b|\bfederation\b|\bunion\s+des\b")

#: Land and property: firms that hold, develop or let ground.
LAND_PROPERTY = re.compile(
    r"(?i)\bfonci[eè]re?\b|\bimmobili[eè]re?s?\b|\bimmobili\b|\blands?\b|"
    r"\bestates?\b|\bdomaines?\b|\bterrains?\b|\blotissement\b|"
    r"\bproprietes\b|\bgerance\s+immobili")

#: Agriculture and the processing of what it grows.
AGRICULTURE = re.compile(
    r"(?i)\bagricole\b|\bagriculture\b|\bagricultural\b|\bagraire\b|"
    r"\begrenage\b|\bginning\b|\bsucreries?\b|\bsugar\b|\brizeries?\b|"
    r"\brice\s+mills?\b|\bhuileries?\b|\bmoulins?\b|\bvignobles?\b|"
    r"\belevage\b|\birrigation\b|\bplantations?\b|\bfermes?\b")

#: Sectors in the order :func:`sector` tries them. **Finance comes first on
#: purpose.** A mortgage bank and an agricultural bank lend against land; they
#: do not hold it. Putting land or agriculture first would move 25 firms and
#: 19 firms respectively out of finance, and would count the Crédit Foncier
#: Égyptien and the Land Bank of Egypt as landholders.
SECTOR_ORDER = ("finance", "land_property", "agriculture")

#: Words left out of every sector on purpose. *Bourse* and *exchange* are
#: market institutions, and these labels do not separate the securities
#: exchange from the cotton exchange reliably enough to be worth coding.
#: *Coton* and *cotton* are left out because they span growing, ginning,
#: pressing, broking and export, and the name rarely says which.
EXCLUDED_VOCABULARY = ("bourse", "exchange", "coton", "cotton")


def is_financial(label: str) -> bool:
    """Does this company name belong to a bank, insurer or credit house?"""
    return sector(label) == "finance"


def sector(label: str) -> str:
    """The firm's sector from its printed name: the first rule that matches.

    Returns ``finance``, ``land_property``, ``agriculture`` or ``other``.
    ``other`` is not a residual claim about the firm — it means none of the
    three vocabularies matched, which for most industrial and trading firms it
    will not.
    """
    text = unidecode(str(label))
    if NOT_A_FIRM.search(text):
        return "other"
    patterns = {"finance": FINANCIAL, "land_property": LAND_PROPERTY,
                "agriculture": AGRICULTURE}
    for name in SECTOR_ORDER:
        if patterns[name].search(text):
            return name
    return "other"


#: Land and agriculture together: the nearest thing this source has to an
#: agrarian interest, and not the same thing as landownership. See
#: `docs/SECTORS.md`.
AGRARIAN = ("land_property", "agriculture")

SECTOR_LABEL = {
    "finance": "Finance",
    "land_property": "Land and property",
    "agriculture": "Agriculture and processing",
    "other": "Everything else",
}


def firm_sectors(companies: pd.DataFrame) -> pd.DataFrame:
    """One row per firm with its sector."""
    out = companies[["company_id", "label"]].copy()
    out["sector"] = out.label.map(sector)
    out["financial"] = out.sector == "finance"
    return out


def financier_panel(processed=None) -> pd.DataFrame:
    """The office panel with one set of columns per sector merged in.

    For each sector: `n_<sector>` seats held in the wave, a boolean, and a
    share of the director's own seats. `financier` and `fin_share` are the
    finance pair, kept under those names because the finance figure and its
    tests use them. `agrarian` is land and agriculture together.

    Also adds `seat_cat`, the stratifying variable every comparison here needs.
    """
    from pathlib import Path

    from . import config
    from .politics import office_panel

    processed = Path(processed) if processed else config.PROCESSED
    aff = pd.read_csv(processed / "affiliations.csv")
    aff["sector"] = aff.company_label.map(sector)

    panel = office_panel(processed)
    for name in SECTOR_ORDER:
        counts = (aff[aff.sector == name].groupby(["year", "person_id"])
                  .company_id.nunique().rename(f"n_{name}").reset_index())
        panel = panel.merge(counts, on=["year", "person_id"], how="left")
        panel[f"n_{name}"] = panel[f"n_{name}"].fillna(0).astype(int)
        panel[name] = panel[f"n_{name}"] > 0
        panel[f"share_{name}"] = panel[f"n_{name}"] / panel.seats

    panel["n_agrarian"] = panel[[f"n_{s}" for s in AGRARIAN]].sum(axis=1)
    panel["agrarian"] = panel.n_agrarian > 0
    panel["share_agrarian"] = panel.n_agrarian / panel.seats
    # The finance figure and its tests were written against these names.
    panel["n_fin"] = panel.n_finance
    panel["financier"] = panel.finance
    panel["fin_share"] = panel.share_finance
    panel["seat_cat"] = panel.seats.clip(upper=5)
    return panel


def firm_side(processed=None) -> dict[str, float]:
    """What financial firms look like from the firm side, not the person side.

    Reported so the reader can see the arithmetic rather than take the
    director-side comparison on trust.
    """
    from pathlib import Path

    from . import config
    from .origin import is_person

    processed = Path(processed) if processed else config.PROCESSED
    aff = pd.read_csv(processed / "affiliations.csv")
    aff = aff[aff.person_label.map(is_person)]
    aff["sector"] = aff.company_label.map(sector)
    board = (aff.groupby(["year", "company_id"])
             .agg(directors=("person_id", "nunique"),
                  sector=("sector", "first")).reset_index())
    facts = {"firm_waves": len(board)}
    for name in (*SECTOR_ORDER, "other"):
        mask = board.sector == name
        facts[f"{name}_firm_waves"] = int(mask.sum())
        facts[f"{name}_share"] = float(mask.mean())
        facts[f"{name}_directors"] = float(board.directors[mask].mean())
        facts[f"{name}_directorship_share"] = float((aff.sector == name).mean())
    agrarian = board.sector.isin(AGRARIAN)
    facts["agrarian_firm_waves"] = int(agrarian.sum())
    facts["agrarian_share"] = float(agrarian.mean())
    facts["agrarian_directors"] = float(board.directors[agrarian].mean())
    facts["agrarian_directorship_share"] = float(aff.sector.isin(AGRARIAN).mean())
    # Names the finance figure was written against.
    facts["financial_share"] = facts["finance_share"]
    facts["directorship_share"] = facts["finance_directorship_share"]
    facts["directors_financial"] = facts["finance_directors"]
    facts["directors_other"] = float(board.directors[~(board.sector == "finance")].mean())
    return facts


def stratified_gap(panel: pd.DataFrame, measure: str, term: str = "financier",
                   n_perm: int = 3000, seed: int = 3,
                   min_cell: int = 8) -> dict:
    """Compare inside wave × seat-count cells, with a within-cell null.

    Directors are compared only with directors of the same wave holding the
    same number of seats, and the null permutes *term* inside each cell — so
    the seat-count arithmetic that produces the raw gap is held exactly fixed
    and cannot appear in the result.

    One-seat cells contribute nothing: every director holding a single seat
    has zero projected betweenness, so they all tie and the cell difference is
    exactly zero by construction.
    """
    rng = np.random.default_rng(seed)
    frame = panel.reset_index(drop=True)
    flag = frame[term].to_numpy().astype(bool)
    values = frame[measure].to_numpy()
    cells = [np.asarray(i) for i in
             frame.groupby(["year", "seat_cat"]).indices.values()]
    usable = [c for c in cells
              if flag[c].sum() >= min_cell and (~flag[c]).sum() >= min_cell]

    def pooled(mark: np.ndarray) -> float:
        num = den = 0.0
        for c in usable:
            a, b = mark[c], ~mark[c]
            w = a.sum() * b.sum() / (a.sum() + b.sum())
            num += (values[c][a].mean() - values[c][b].mean()) * w
            den += w
        return num / den if den else float("nan")

    observed = pooled(flag)
    draws = np.empty(n_perm)
    for i in range(n_perm):
        shuffled = flag.copy()
        for c in usable:
            v = shuffled[c].copy()
            rng.shuffle(v)
            shuffled[c] = v
        draws[i] = pooled(shuffled)

    raw = values[flag].mean() - values[~flag].mean()
    return {"measure": measure, "raw": raw, "within_cells": observed,
            "p_perm": float(np.mean(np.abs(draws) >= abs(observed))),
            "null_lo": float(np.percentile(draws, 2.5)),
            "null_hi": float(np.percentile(draws, 97.5)),
            "cells": len(usable), "n": int(flag.sum())}


def financier_rate_by_seats(panel: pd.DataFrame, term: str = "political",
                            min_n: int = 8) -> pd.DataFrame:
    """Share holding a financial seat, by seat count, split on *term*.

    The point of the split is that office holders hold more seats, so their
    higher financier rate could be arithmetic. Reading it seat count by seat
    count removes that.
    """
    rows = []
    for seats, chunk in panel.groupby("seat_cat"):
        a, b = chunk[chunk[term]], chunk[~chunk[term]]
        if len(a) < min_n or len(b) < min_n:
            continue
        rows.append({"seats": int(seats), "with_term": a.financier.mean() * 100,
                     "without_term": b.financier.mean() * 100,
                     "n_with": len(a), "n_without": len(b)})
    return pd.DataFrame(rows)
