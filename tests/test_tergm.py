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


def test_change_statistics_are_the_right_shape(panel):
    """One row per at-risk dyad, and the memory term must count the ties that
    existed at t-1 among exactly those dyads."""
    from politi.tergm import TERMS, change_statistics, transition_table

    design = change_statistics(panel)
    table = transition_table(panel).set_index("to")
    assert set(design.columns) == {"year", "person_id", "company_id", "tie",
                                   *TERMS}
    assert (design.edges == 1).all()          # the intercept
    for year, chunk in design.groupby("year"):
        assert len(chunk) == table.loc[year, "dyads_at_risk"]
        assert chunk.tie.sum() == table.loc[year, "edges_to"]
        assert chunk.memory.sum() == table.loc[year, "edges_from"]
    # 1932 is only a lag: the first modelled wave is the second in the panel.
    assert sorted(design.year.unique()) == panel["waves"][1:]


def test_degree_change_statistics_exclude_the_focal_tie():
    """The change statistic of a two-star is the partner count the new tie
    would join, which must not include the tie itself."""
    from politi.tergm import change_statistics

    # One director on two firms in both waves; one firm with two directors.
    panel = {
        "waves": [1, 2],
        "edges": {y: pd.DataFrame({"person_id": ["p1", "p1", "p2"],
                                   "company_id": ["c1", "c2", "c1"]})
                  for y in (1, 2)},
        "persons": {y: pd.DataFrame({"person_id": ["p1", "p2"],
                                     "origin": ["european", "european"],
                                     "political": [False, False]})
                    for y in (1, 2)},
        "firms": {y: pd.DataFrame({"company_id": ["c1", "c2"],
                                   "sector": ["other", "other"]})
                  for y in (1, 2)},
    }
    d = change_statistics(panel).set_index(["person_id", "company_id"])
    # p1 holds c1 and c2, so toggling either leaves one other seat.
    assert d.loc[("p1", "c1"), "b1star2"] == 1
    # c1 already has p1 and p2; toggling p2-c1 leaves one other director.
    assert d.loc[("p2", "c1"), "b2star2"] == 1
    # p2 does not hold c2. Adding it would join p2's one existing seat, and
    # on the firm side would join p1, who already sits on c2.
    assert d.loc[("p2", "c2"), "b1star2"] == 1
    assert d.loc[("p2", "c2"), "b2star2"] == 1
    # Same-origin board-mates, excluding ego: p1 and p2 share c1, and c2
    # holds only p1, so ego there has nobody to match.
    assert d.loc[("p2", "c1"), "origin_match"] == 1
    assert d.loc[("p1", "c2"), "origin_match"] == 0
    # Adding p2 to c2 would seat him beside p1, of the same origin.
    assert d.loc[("p2", "c2"), "origin_match"] == 1
