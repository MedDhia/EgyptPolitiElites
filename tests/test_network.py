"""Affiliation network construction and its projections."""

from pathlib import Path

import pytest

from politi.build import build_tables
from politi.export import export_all
from politi.network import (
    BOARD_ROLES, build_bipartite, company_projection, describe, dynamic_graph,
    person_projection,
)
from politi.parse import parse_volume

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_volume.txt"


@pytest.fixture(scope="module")
def tables():
    return build_tables({1932: parse_volume(FIXTURE.read_text(encoding="utf-8"))})


def test_affiliation_table_shape(tables):
    aff = tables["affiliations"]
    assert len(aff) == 20                     # every printed directorship
    assert set(aff.columns) >= {"person_id", "company_id", "role", "year", "source_page"}
    assert aff["year"].unique().tolist() == [1932]


def test_a_person_on_two_boards_is_one_node(tables):
    aff = tables["affiliations"]
    zohdy = aff[aff["person_label"] == "Faridoun Zohdy"]
    assert len(zohdy) == 2                     # two companies
    assert zohdy["person_id"].nunique() == 1


def test_bipartite_graph_has_two_modes(tables):
    g = build_bipartite(tables["affiliations"].to_dict("records"))
    kinds = {d["kind"] for _, d in g.nodes(data=True)}
    assert kinds == {"person", "company"}
    # No person-person or company-company edge may exist in a two-mode graph.
    for a, b in g.edges():
        assert g.nodes[a]["kind"] != g.nodes[b]["kind"]


def test_auditors_are_excluded_from_the_default_tie_definition(tables):
    assert "auditor" not in BOARD_ROLES
    rows = tables["affiliations"].to_dict("records")
    g = build_bipartite(rows)
    labels = {d.get("label") for _, d in g.nodes(data=True)}
    assert "Léonce Tabbagh" not in labels      # auditor on two boards, not a tie
    assert "Faridoun Zohdy" in labels


def test_interlock_weight_counts_shared_directors(tables):
    g = build_bipartite(tables["affiliations"].to_dict("records"))
    firms = company_projection(g)
    by_label = {d["label"]: n for n, d in firms.nodes(data=True)}
    eaux = by_label["SOCIETE ANONYME FICTIVE DES EAUX DE MAHROUSSA"]
    sucr = by_label["COMPAGNIE FICTIVE DES SUCRERIES DE BENI-KHALDA"]
    # Zohdy, Palamède and Vasconi sit on both boards; Tabbagh audits both.
    assert firms[eaux][sucr]["weight"] == 3


def test_projection_records_who_carries_the_tie(tables):
    g = build_bipartite(tables["affiliations"].to_dict("records"))
    firms = company_projection(g)
    a, b, data = next(iter(firms.edges(data=True)))
    assert data["via"], "each interlock must name the directors that create it"
    assert len(data["via"].split(";")) == data["weight"]


def test_person_projection_is_symmetric_in_meaning(tables):
    g = build_bipartite(tables["affiliations"].to_dict("records"))
    people = person_projection(g)
    assert people.number_of_nodes() == 9
    assert all(d["weight"] >= 1 for _, _, d in people.edges(data=True))


def test_describe_handles_an_empty_graph():
    import networkx as nx
    assert describe(nx.Graph())["nodes"] == 0


def test_dynamic_graph_marks_wave_membership(tables):
    g = build_bipartite(tables["affiliations"].to_dict("records"))
    merged = dynamic_graph({1932: g, 1938: g})
    node = next(iter(merged.nodes()))
    assert merged.nodes[node]["years"] == "1932;1938"
    assert merged.nodes[node]["y1932"] is True


def test_export_writes_the_expected_artefacts(tables, tmp_path):
    written = export_all(tables, tmp_path)
    assert (tmp_path / "affiliations.csv").exists()
    assert (tmp_path / "network_summary.csv").exists()
    assert (tmp_path / "graphs" / "company_interlocks_1932.gexf").exists()
    assert (tmp_path / "graphs" / "affiliation_1932.graphml").exists()
    assert written["tables"] and written["graphs"]
