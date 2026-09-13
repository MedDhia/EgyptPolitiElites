"""Embeddedness against structural holes.

The tests here are about the *statistics*, not the findings: a four-cycle
count computed wrongly would produce a confident answer to the wrong question.
"""

import numpy as np
import pandas as pd
import pytest

from politi.holes import (BROKERAGE, CLOSURE_TERMS, brokerage_panel,
                          closure_design, distance_table, _mates, _wave_state,
                          _distance_to_firms)


@pytest.fixture(scope="module")
def toy():
    """Four directors, three firms. A, B and D share f1; B also sits on f2.

    So A is at distance 3 from f2 with exactly one prior board-mate on it
    (B), his two alters B and D share f1 with each other, and f3 is
    unreachable from all three.
    """
    edges = pd.DataFrame([("A", "f1"), ("B", "f1"), ("D", "f1"),
                          ("B", "f2"), ("C", "f3")],
                         columns=["person_id", "company_id"])
    persons = pd.DataFrame({"person_id": ["A", "B", "C", "D"],
                            "origin": ["european", "european", "unknown",
                                       "european"],
                            "political": [True, False, False, False],
                            "rank": "untitled"})
    firms = pd.DataFrame({"company_id": ["f1", "f2", "f3"],
                          "sector": ["other", "finance", "other"]})
    return {"waves": [1, 2],
            "edges": {1: edges, 2: edges},
            "persons": {1: persons, 2: persons},
            "firms": {1: firms, 2: firms}}


def test_mates_are_weighted_by_shared_boards(toy):
    state = _wave_state(toy, 1)
    assert _mates(state, "A") == {"B": 1, "D": 1}
    assert _mates(state, "B") == {"A": 1, "D": 1}
    assert _mates(state, "C") == {}


def test_distance_is_odd_and_marks_unreachable(toy):
    state = _wave_state(toy, 1)
    d = _distance_to_firms(state, "A", ["f1", "f2", "f3"])
    assert d == {"f1": 1, "f2": 3, "f3": -1}


def test_closure_is_positive_exactly_at_distance_three(toy):
    d = closure_design(toy)
    form = d[d.memory == 0]
    assert ((form.closure > 0) == (form.distance == 3)).all()
    row = form[(form.person_id == "A") & (form.company_id == "f2")].iloc[0]
    assert row.closure == 1 and row.closure4 == 1 and row.distance == 3


def test_a_held_seat_does_not_count_as_its_own_closure(toy):
    """A and B share f1. Toggling A's existing f1 tie must not count B as a
    path, because the only board joining them is f1 itself."""
    d = closure_design(toy)
    row = d[(d.person_id == "A") & (d.company_id == "f1")].iloc[0]
    assert row.memory == 1
    assert row.closure == 0 and row.closure4 == 0


def test_prior_mates_is_in_the_specification():
    """The closure count is |mates & board|, so the mates count is not an
    optional control -- without it the term absorbs contact volume."""
    assert "prior_mates" in CLOSURE_TERMS
    assert "prior_board" in CLOSURE_TERMS


def test_expected_closure_is_the_random_matching_benchmark(toy):
    d = closure_design(toy)
    n = len(set(toy["persons"][1].person_id))
    row = d[(d.person_id == "A") & (d.company_id == "f2")].iloc[0]
    assert row.closure_expected == pytest.approx(row.prior_mates
                                                 * row.prior_board / n)
    assert row.closure_excess == pytest.approx(row.closure - row.closure_expected)


def test_distance_table_bands_are_labelled(toy):
    table = distance_table(closure_design(toy))
    assert set(table.band) <= {"unreachable", "3 (a board-mate sits on it)",
                               "5 (two steps out)", "7 or more"}
    assert (table.rate_per_1000 <= 1000).all()


def test_brokerage_drops_the_last_wave(toy):
    """The last wave has no successor, so it carries no outcome."""
    b = brokerage_panel(toy)
    assert set(b.year) == {1}
    assert set(b.next_year) == {2}


def test_open_share_is_zero_when_every_alter_pair_shares_a_board(toy):
    """A sits only on f1, so both his alters sit on f1 with each other and no
    pair of them is open. This is why one-seat directors are excluded from the
    brokerage test: their score is 0 by construction, not by behaviour.

    B, who sits on f1 and f2, has the same two alters and the same score,
    because D and A also share f1 -- a reminder that open_share measures the
    alters' ties, not the ego's spread."""
    b = brokerage_panel(toy).set_index("person_id")
    assert b.loc["A", "open_share"] == 0.0
    assert np.isnan(b.loc["C", "open_share"])     # no alters, so no pairs


# --- the real dataset ---------------------------------------------------------

@pytest.fixture(scope="module")
def real():
    from politi.tergm import network_panel
    return network_panel()


def test_closure_design_matches_the_tergm_at_risk_sets(real):
    from politi.tergm import change_statistics

    a = closure_design(real)
    b = change_statistics(real)
    assert len(a) == len(b)
    left = set(map(tuple, a[["year", "person_id", "company_id"]].to_numpy()))
    right = set(map(tuple, b[["year", "person_id", "company_id"]].to_numpy()))
    assert left == right


def test_memory_agrees_with_the_tergm_design(real):
    from politi.tergm import change_statistics

    key = ["year", "person_id", "company_id"]
    a = closure_design(real).set_index(key).sort_index()
    b = change_statistics(real).set_index(key).sort_index()
    assert (a.memory.to_numpy() == b.memory.to_numpy()).all()
    assert (a.tie.to_numpy() == b.tie.to_numpy()).all()


def test_brokerage_measures_are_bounded(real):
    b = brokerage_panel(real)
    assert b.open_share.dropna().between(0, 1).all()
    assert (b.effective_size.dropna() >= 0).all()
    assert (b.constraint.dropna() >= 0).all()
    for column in BROKERAGE:
        assert b.loc[b.seats >= 2, column].notna().any()


def test_effective_size_is_nearly_contact_volume(real):
    """Boards are cliques, so a director's alters within one board are wholly
    redundant and Burt's correction recovers little beyond how many alters he
    has. The correlation is reported in the docs as a limit on what effective
    size can test here, so it is pinned."""
    b = brokerage_panel(real)
    m = b[b.seats >= 2].dropna(subset=["effective_size"])
    assert m.effective_size.corr(m.mates) > 0.9
