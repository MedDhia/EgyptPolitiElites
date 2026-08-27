"""Coding directors by community of origin."""

import pytest

from politi.origin import ARAB, EUROPEAN, MINORITY, UNKNOWN, classify, is_person


@pytest.mark.parametrize("name,expected", [
    ("S.E. Cattaui Pacha Joseph A.", MINORITY),      # Egyptian Jewish
    ("Mosseri Elie N", MINORITY),
    ("Choremi Constantin Jean", MINORITY),           # Greek
    ("Tanielian Berge", MINORITY),                   # Armenian
    ("Sursock Wladimir", MINORITY),                  # Syro-Lebanese
    ("Naus Bey Henri C.B.E.", EUROPEAN),             # Belgian
    ("Barker Henry", EUROPEAN),                      # British
    ("Abdel Hamid Badaoui Pacha", ARAB),
    ("Mohamed Mahmoud Bey Khalil", ARAB),
    ("Ahmed Abboud Pacha", ARAB),
])
def test_known_directors(name, expected):
    assert classify(name).group == expected


def test_a_european_given_name_is_not_evidence_of_european_origin():
    """Regression: 'nicolas' sat in a French surname lexicon, so Bassili — a
    Copt — was classified European. The contrast under study is European vs
    Egyptian, so this error pushed straight on the estimand."""
    assert classify("Bassili Nicolas Alexandre").group == MINORITY
    assert classify("Joseph Cattaui").group == MINORITY
    assert classify("Élie Mosseri").group == MINORITY


def test_titles_are_not_evidence_of_origin():
    """Bey and Pacha were held across every community here."""
    assert classify("Barker Bey Henry").group == EUROPEAN
    assert classify("Cattaui Pacha Joseph").group == MINORITY


def test_unclassifiable_names_are_not_guessed():
    assert classify("Xqzv Wprt").group == UNKNOWN
    assert classify("").group == UNKNOWN


@pytest.mark.parametrize("junk", [
    "Grand Officier Couronne Belge", "Ancien Ministre", "Le Caire",
    "Linen Industry", "Comité Gouvernemental des Textiles",
    "Etudes: American College Smyrne", "Nil B.A. Oxford University F.R.G.S",
])
def test_non_persons_are_excluded(junk):
    assert not is_person(junk)


@pytest.mark.parametrize("real", [
    "Cattaui Pacha Joseph A.", "Barker Henry", "Abdel Hamid Badaoui",
])
def test_real_directors_survive_the_filter(real):
    assert is_person(real)


def test_the_journal_figure_set_builds(tmp_path):
    """Every figure in the manuscript's appendix has a counterpart here."""
    import warnings

    import numpy as np
    import pandas as pd

    from politi.figures_journal import build_all

    rng = np.random.default_rng(0)
    n = 240
    panel = pd.DataFrame({
        "year": rng.choice([1932, 1938, 1942, 1947, 1950], n),
        "person_id": [f"P{i:04d}" for i in range(n)],
        "person_label": [f"Person {i}" for i in range(n)],
        "betweenness": np.where(rng.random(n) < 0.6, 0.0, rng.random(n) * 0.05),
        "degree": rng.integers(1, 6, n),
        "closeness": rng.random(n),
        "clustering": rng.random(n),
        "origin": pd.Categorical(
            rng.choice(["arab_egyptian", "european", "local_minority"], n),
            categories=["arab_egyptian", "european", "local_minority", "unknown"]),
    })
    panel["bc_scaled"] = panel.betweenness * 1000
    panel["bc_count"] = panel.bc_scaled.round().astype(int)
    panel["bc_log"] = np.log1p(panel.bc_scaled)
    for col in ("degree", "closeness", "clustering"):
        panel[f"{col}_z"] = panel.groupby("year")[col].transform(
            lambda s: (s - s.mean()) / (s.std(ddof=0) or 1.0))
    panel["deg_proj_z"] = panel.degree_z
    panel["bcp_log"] = panel.bc_log

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        made = build_all(panel, tmp_path, n_perm=200)
    assert len(made) == 10
    for path in made:
        assert path.exists() and path.stat().st_size > 1000
