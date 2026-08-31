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

#: Public and professional bodies whose names carry a financial word — a
#: ministry of finance, a committee on reinsurance — and which are not firms.
NOT_A_FIRM = re.compile(
    r"(?i)\bminist[eè]re\b|\bcomit[eé]\b|\bcommission\b|"
    r"\bconseil\s+(?:sup|cons)|\bchambre\b|\bsyndicat\b|\bassociation\b|"
    r"\bfederation\b")

#: Words left out of :data:`FINANCIAL` on purpose.
#:
#: *Foncier* and *immobilier* are land and property, not credit — "Société
#: Foncière d'Égypte" is a land company, while "Crédit Foncier Égyptien" is a
#: mortgage bank and is caught by *crédit*. *Bourse* and *exchange* are market
#: institutions, and the commodity exchanges cannot be told from the
#: securities exchange reliably enough in these labels to be worth coding.
EXCLUDED_VOCABULARY = ("foncier", "immobilier", "land", "estates", "bourse",
                       "exchange")


def is_financial(label: str) -> bool:
    """Does this company name belong to a bank, insurer or credit house?"""
    text = unidecode(str(label))
    return bool(FINANCIAL.search(text)) and not NOT_A_FIRM.search(text)


def firm_sectors(companies: pd.DataFrame) -> pd.DataFrame:
    """One row per firm with the sector flag."""
    out = companies[["company_id", "label"]].copy()
    out["financial"] = out.label.map(is_financial)
    return out


def financier_panel(processed=None) -> pd.DataFrame:
    """The office panel with the financial-sector columns merged in.

    Adds `n_fin` (financial seats held in the wave), `financier` (any), and
    `fin_share` (the share of this director's seats that are financial), plus
    `seat_cat`, the stratifying variable every comparison here needs.
    """
    from pathlib import Path

    from . import config
    from .politics import office_panel

    processed = Path(processed) if processed else config.PROCESSED
    aff = pd.read_csv(processed / "affiliations.csv")
    aff["financial"] = aff.company_label.map(is_financial)
    counts = (aff[aff.financial].groupby(["year", "person_id"]).company_id
              .nunique().rename("n_fin").reset_index())

    panel = office_panel(processed).merge(counts, on=["year", "person_id"],
                                          how="left")
    panel["n_fin"] = panel.n_fin.fillna(0).astype(int)
    panel["financier"] = panel.n_fin > 0
    panel["fin_share"] = panel.n_fin / panel.seats
    #: Capped so the top cell is not one director.
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
    aff["financial"] = aff.company_label.map(is_financial)
    board = (aff.groupby(["year", "company_id"])
             .agg(directors=("person_id", "nunique"),
                  financial=("financial", "first")).reset_index())
    return {
        "firm_waves": len(board),
        "financial_firm_waves": int(board.financial.sum()),
        "financial_share": float(board.financial.mean()),
        "directors_financial": float(board.directors[board.financial].mean()),
        "directors_other": float(board.directors[~board.financial].mean()),
        "directorship_share": float(aff.financial.mean()),
    }


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
