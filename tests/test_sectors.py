"""Coding firm sector, and the seat-count trap it creates."""

import numpy as np
import pandas as pd
import pytest

from politi.sectors import (financier_rate_by_seats, is_financial,
                            stratified_gap)


@pytest.mark.parametrize("label,expected", [
    ("Banque Misr", True),
    ("National Bank of Egypt", True),
    ("Banco Italo-Egiziano", True),
    ("Crédit Foncier Egyptien", True),          # a mortgage bank
    ("Alexandria Insurance Co", True),
    ("Caisse Hypothécaire d'Egypte", True),
    ("Société Financière et Industrielle d'Egypte", True),
    ("The Mortgage Co. of Egypt Ltd", True),
    # Land and property are not credit.
    ("Société Foncière d'Egypte", False),
    ("Dakahlieh Land Co", False),
    ("Crédit Immobilier Suisse-Egyptien", True),   # 'crédit' carries it
    ("The Cairo Suburban Building Land Co", False),
    # Market institutions are left out.
    ("Bourse des Marchandises", False),
    ("Alexandria Exchange Co", False),
    # Public bodies that carry a financial word are not firms.
    ("Consultatif des Réassurances au Ministère du Travail", False),
    ("Comité de Londres de The Mortgage Co. Ltd", False),
    # Ordinary industry.
    ("Filature Nationale d'Egypte", False),
])
def test_is_financial(label, expected):
    assert is_financial(label) is expected


def test_stratified_gap_removes_a_pure_seat_count_artefact():
    """The trap the module exists for.

    Financial seats are assigned at random, so a director with more seats is
    likelier to hold one — and centrality rises with seats. The raw gap must
    be large and the within-cell gap must vanish.
    """
    rng = np.random.default_rng(0)
    seats = rng.integers(1, 6, 1200)
    # One directorship in eight is financial, assigned with no regard to the
    # director; centrality is a pure function of seat count.
    financier = np.array([rng.random(s).min() < 0.125 for s in seats])
    panel = pd.DataFrame({
        "year": 1938, "seat_cat": seats, "financier": financier,
        "pct_x": seats * 15 + rng.normal(0, 3, 1200),
    })
    out = stratified_gap(panel, "pct_x", n_perm=400, seed=1, min_cell=20)
    assert out["raw"] > 8            # the artefact is large
    assert abs(out["within_cells"]) < 3
    assert out["p_perm"] > 0.05


def test_stratified_gap_keeps_a_real_within_cell_gap():
    rng = np.random.default_rng(2)
    seats = rng.integers(1, 6, 1200)
    financier = rng.random(1200) < 0.4
    panel = pd.DataFrame({
        "year": 1938, "seat_cat": seats, "financier": financier,
        "pct_x": seats * 15 + financier * 12 + rng.normal(0, 3, 1200),
    })
    out = stratified_gap(panel, "pct_x", n_perm=400, seed=1, min_cell=20)
    assert out["within_cells"] > 8
    assert out["p_perm"] < 0.01


def test_financier_rate_by_seats_drops_thin_rows():
    panel = pd.DataFrame({
        "seat_cat": [1] * 30 + [2] * 5,
        "political": [True] * 15 + [False] * 15 + [True] * 5,
        "financier": [True] * 10 + [False] * 25,
    })
    out = financier_rate_by_seats(panel)
    assert list(out.seats) == [1]
