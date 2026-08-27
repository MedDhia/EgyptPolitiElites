"""Coding public office out of the roster entries."""

import pandas as pd
import pytest

from politi.biographies import parse_entry
from politi.politics import (attach_offices, find_offices, firm_flags,
                             person_flags)


@pytest.mark.parametrize("entry,expected", [
    # A portfolio is cabinet; the qualifier makes it past.
    ("Ancien Ministre des Finances", {"cabinet": True}),
    ("Ministre des Wakfs", {"cabinet": False}),
    # Both chambers.
    ("Sénateur du Royaume", {"parliament": False}),
    ("Ancien Député de Gamalieh", {"parliament": True}),
    # A diplomatic 'ministre' is not a cabinet post.
    ("Ministre Plénipotentiaire", {"diplomatic": False}),
    ("Ancien Ministre d'Egypte à Paris", {"diplomatic": True}),
    # Provincial administration, and the two things that borrow its word.
    ("Ancien Gouverneur de la Ville d'Alexandrie", {"provincial": True}),
    ("Moudir d'Assouan", {"provincial": False}),
    ("Gouverneur de la National Bank of Egypt", {}),
    ("Ancien Gouverneur du 83ème District du Rotary Club", {}),
    # Bench and town hall.
    ("Ancien Magistrat", {"judicial": True}),
    ("Ancien Conseiller Municipal", {"municipal": True}),
    # A plain directorship names no office.
    ("Administrateur de la Sté. Anonyme des Ciments", {}),
])
def test_find_offices(entry, expected):
    assert find_offices(entry) == expected


def test_two_offices_in_one_entry():
    found = find_offices("Sénateur; ancien Ministre; Vice-Président de X")
    assert found == {"parliament": False, "cabinet": True}


def test_office_is_not_part_of_the_name():
    """The user-visible half of the same fact: names carry no offices."""
    for entry, name in [
            ("S.E. Sadek, Wahba (Pacha),Sénateur; ancien Ministre; Adm. de X",
             "Sadek Wahba Pacha"),
            ("Abdel Haï Khalil Bey Député, Adm. de la Sté. X",
             "Abdel Haï Khalil Bey"),
            ("Nakhla Pacha El Motei Ancien Magistrat, Prés. de X",
             "Nakhla Pacha El Motei"),
            # A surname that happens to be an honour word survives intact.
            ("Chevalier, Paul, Adm. de la Sté. X", "Chevalier Paul"),
    ]:
        assert parse_entry(entry).name == name


def test_attach_and_flags():
    offices = pd.DataFrame([
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha",
         "office": "cabinet", "former": True, "source_page": 4884},
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha",
         "office": "parliament", "former": False, "source_page": 4884},
    ])
    # Two mentions of the same man: his ministry must not be counted twice.
    crosswalk = pd.DataFrame([
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha", "person_id": "p1"},
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha", "person_id": "p1"},
    ])
    resolved = attach_offices(offices, crosswalk)
    assert len(resolved) == 2

    flags = person_flags(resolved)
    row = flags.iloc[0]
    assert row.n_offices == 2 and row.political and row.national
    assert not row.all_former          # the senate seat is current

    aff = pd.DataFrame([
        {"year": 1947, "person_id": "p1", "company_id": "c1"},
        {"year": 1947, "person_id": "p2", "company_id": "c1"},
        {"year": 1947, "person_id": "p2", "company_id": "c2"},
    ])
    firms = firm_flags(aff, flags).set_index("company_id")
    assert bool(firms.loc["c1", "connected"])
    assert firms.loc["c1", "share_political"] == 0.5
    assert not bool(firms.loc["c2", "connected"])


def test_firm_counts_are_integers():
    """A one-director firm must count 0 political directors, not False.

    Summing an object-dtype boolean column returns `False` for a single-row
    group, which then reads back from CSV as the string "False".
    """
    aff = pd.DataFrame([{"year": 1947, "person_id": "p1", "company_id": "c1"}])
    flags = pd.DataFrame(columns=["year", "person_id", "political", "national"])
    firms = firm_flags(aff, flags)
    assert firms.n_political.dtype.kind == "i"
    assert firms.n_national.dtype.kind == "i"
    assert firms.loc[0, "n_political"] == 0


def test_flags_are_empty_not_broken_without_offices():
    flags = person_flags(pd.DataFrame(columns=["year", "person_id", "office",
                                               "former"]))
    assert flags.empty and "political" in flags.columns


def test_persistence_stratified_finds_nothing_when_there_is_nothing():
    """A cell where connection is unrelated to reappearance must pool to ~0."""
    import numpy as np

    from politi.politics import persistence_stratified

    rng = np.random.default_rng(0)
    n = 400
    panel = pd.DataFrame({
        "year": 1938,
        "company_id": [f"c{i}" for i in range(n)],
        "directors_cat": rng.integers(1, 4, n),
        "connected": rng.random(n) < 0.4,
    })
    # Reappearance depends on the stratum only, never on connection.
    panel["reappears"] = (rng.random(n) < panel.directors_cat / 5).astype(int)
    out = persistence_stratified(panel, n_perm=300, seed=2)
    assert abs(out["pooled_pts"]) < 12
    assert out["p_perm"] > 0.05
    assert out["n_cells"] == 3


def test_persistence_stratified_recovers_a_planted_difference():
    """And must find one when it is there, so the null above means something."""
    import numpy as np

    from politi.politics import persistence_stratified

    rng = np.random.default_rng(1)
    n = 400
    connected = rng.random(n) < 0.5
    panel = pd.DataFrame({
        "year": 1938, "company_id": [f"c{i}" for i in range(n)],
        "directors_cat": 2, "connected": connected,
        "reappears": (rng.random(n) < np.where(connected, 0.85, 0.35)).astype(int),
    })
    out = persistence_stratified(panel, n_perm=300, seed=2)
    assert out["pooled_pts"] > 30
    assert out["p_perm"] < 0.01


def test_survival_panel_shape():
    """The risk set: one row per wave at risk, none for the last wave."""
    from politi.politics import survival_panel

    panel = survival_panel()
    # Every row has an interval to the next wave, and none starts at 1950.
    assert panel.gap.between(3, 6).all()
    assert 1950 not in set(panel.year)
    # Tenure starts at 1 and never skips within a firm.
    for _, g in panel.groupby("company_id"):
        t = sorted(g.tenure)
        assert t == list(range(t[0], t[0] + len(t)))
        assert t[0] == 1
    # A firm with an exit contributes no later row: the spell is over.
    ended = panel[panel.exit == 1]
    for cid, year in zip(ended.company_id, ended.year):
        assert panel[(panel.company_id == cid) & (panel.year > year)].empty


def test_permanent_exit_keeps_firms_that_come_back():
    """Under the alternative coding an internal gap is not an exit."""
    from politi.politics import survival_panel

    first = survival_panel()
    permanent = survival_panel(permanent_exit=True)
    assert len(permanent) > len(first)
    assert permanent.exit.sum() < first.exit.sum()


def test_life_table_survival_is_the_product_of_one_minus_hazard():
    from politi.politics import life_table

    panel = pd.DataFrame({
        "company_id": [f"c{i}" for i in range(30)],
        "tenure_cat": [1] * 20 + [2] * 10,
        "exit": [1] * 10 + [0] * 10 + [1] * 2 + [0] * 8,
    })
    t = life_table(panel).set_index("tenure_cat")
    assert t.loc[1, "hazard"] == pytest.approx(0.5)
    assert t.loc[2, "hazard"] == pytest.approx(0.2)
    assert t.loc[2, "survival"] == pytest.approx(0.5 * 0.8)


def test_baseline_connection_is_fixed_at_entry():
    """A survivor curve cannot be stratified on a covariate that moves."""
    from politi.politics import baseline_connection

    panel = pd.DataFrame({
        "company_id": ["c1", "c1", "c2"],
        "tenure": [1, 2, 1],
        "connected": [True, False, False],
    })
    assert list(baseline_connection(panel)) == [True, True, False]
