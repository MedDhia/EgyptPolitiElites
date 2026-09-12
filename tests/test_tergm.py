"""The network panel a temporal ERGM is fitted to."""

import pandas as pd
import pytest

from politi.tergm import network_panel, transition_table


@pytest.fixture(scope="module")
def panel():
    return network_panel()


def test_panel_has_every_wave(panel):
    assert panel["waves"] == [1932, 1938, 1942, 1947, 1950]
    for year in panel["waves"]:
        assert not panel["edges"][year].empty
        assert not panel["persons"][year].empty
        assert not panel["firms"][year].empty


def test_edges_are_unique_within_a_wave(panel):
    """One row per person-firm seat: a repeated mention is not a second tie."""
    for year in panel["waves"]:
        e = panel["edges"][year]
        assert not e.duplicated().any()


def test_every_edge_endpoint_has_attributes(panel):
    """ergm requires the attribute on every vertex, so no endpoint may be
    missing from the node frames."""
    for year in panel["waves"]:
        e, p, f = (panel["edges"][year], panel["persons"][year],
                   panel["firms"][year])
        assert set(e.person_id) <= set(p.person_id)
        assert set(e.company_id) <= set(f.company_id)
        assert p.origin.notna().all() and (p.origin != "").all()
        assert f.sector.notna().all() and (f.sector != "").all()


def test_origin_is_fixed_across_waves(panel):
    """Origin is a property of the man. An imputation that moved between
    volumes would be a linkage artefact, not a biography."""
    seen = {}
    for year in panel["waves"]:
        for pid, origin in zip(panel["persons"][year].person_id,
                               panel["persons"][year].origin):
            if pid in seen:
                assert seen[pid] == origin
            seen[pid] = origin


def test_transition_table_arithmetic(panel):
    """stable + formed must be the ties at t, and stable + dissolved those at
    t-1, both restricted to the at-risk set."""
    t = transition_table(panel)
    assert len(t) == len(panel["waves"]) - 1
    assert (t.stable + t.formed == t.edges_to).all()
    assert (t.stable + t.dissolved == t.edges_from).all()
    assert (t.dyads_at_risk == t.persons_both * t.firms_both).all()
    # The at-risk set is always a small part of the full network: this is the
    # cost of the design and the table exists to make it visible.
    assert (t.edges_to < t.dyads_at_risk).all()


def test_dropping_1932_changes_the_first_transition(panel):
    """1932's roster is a selection, so the model is reported without it too."""
    later = network_panel(drop_1932=True)
    assert later["waves"] == [1938, 1942, 1947, 1950]
    assert transition_table(later)["from"].iloc[0] == 1938


def test_no_network_derived_covariate_is_exported(panel):
    """A quantity computed from the ties cannot be a covariate: it would
    regress the network on itself. Guard the export against drift."""
    banned = {"seats", "degree", "n_fin", "financier", "btw_proj", "deg_proj",
              "betweenness", "closeness", "pct_seats", "pct_btw_proj"}
    for year in panel["waves"]:
        for frame in (panel["persons"][year], panel["firms"][year]):
            assert not banned & set(frame.columns)
