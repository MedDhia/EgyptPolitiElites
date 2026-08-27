"""Descriptive figures: the non-person filter, and that every figure renders."""

import pandas as pd
import pytest

from politi.explore import build_all, real_directors


def test_real_directors_drops_offices_and_decorations():
    aff = pd.DataFrame({
        "year": [1947] * 4,
        "person_id": ["p1", "p2", "p3", "p4"],
        "person_label": ["Sabry Hussein",
                         "Baehler Charles Commandeur Medjidié",
                         "Grand Officier Couronne Belge",
                         "Comité Gouvernemental des Transports Maritimes"],
        "company_id": ["c1", "c1", "c1", "c1"],
    })
    kept = set(real_directors(aff).person_label)
    assert kept == {"Sabry Hussein", "Baehler Charles Commandeur Medjidié"}


def test_build_all_renders_every_figure(tmp_path):
    """Without an origin panel, the five origin-free figures are still written."""
    pytest.importorskip("matplotlib")
    years = [1932, 1938, 1942, 1947, 1950]
    rows = []
    for y in years:
        for p in range(12):
            for c in range(1 + p % 3):
                rows.append({"year": y, "person_id": f"p{p}",
                             "person_label": f"Hassan Ahmed {p}",
                             "rank": ("pasha", "bey", None)[p % 3],
                             "company_id": f"c{(p + c) % 9}",
                             "company_label": f"Société Anonyme {(p + c) % 9}"})
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(rows).to_csv(processed / "affiliations.csv", index=False)

    made = build_all(processed, tmp_path / "figs")
    assert len(made) == 5
    assert all(p.exists() and p.stat().st_size > 0 for p in made)
