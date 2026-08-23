"""Build the affiliation network and its two projections.

The primitive object is a **two-mode (bipartite) affiliation network**: an edge
joins a person to a company when the annuaire prints that person on that
company's board in that year. Everything else is derived from it:

* ``company_projection`` — the interlocking-directorate network. Two firms are
  tied when they share at least one board member; the weight is the number of
  shared members.
* ``person_projection`` — the co-membership network. Two directors are tied
  when they sit on a board together; the weight is the number of shared boards.

Both projections are *derived* quantities and inherit every error in the
underlying entity resolution, which is why the two-mode edge list is the
artefact of record.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import networkx as nx

# Board roles that constitute a directorship tie. ``manager`` and ``secretary``
# are executive rather than board positions; ``auditor`` (commissaire aux
# comptes) is a statutory outsider. All are captured in the data but excluded
# from the default tie definition — see docs/CODEBOOK.md.
BOARD_ROLES = frozenset(
    {"president", "honorary_president", "vice_president", "managing_director", "director"}
)


def build_bipartite(rows: list[dict], roles: frozenset[str] | None = None) -> nx.Graph:
    """Two-mode graph for one wave. *rows* are affiliation records."""
    roles = BOARD_ROLES if roles is None else roles
    g = nx.Graph()
    for r in rows:
        if r["role"] not in roles:
            continue
        p, c = r["person_id"], r["company_id"]
        g.add_node(p, bipartite=0, kind="person", label=r["person_label"],
                   rank=r.get("rank") or "")
        g.add_node(c, bipartite=1, kind="company", label=r["company_label"],
                   city=r.get("city") or "", capital=r.get("capital_amount") or 0.0)
        g.add_edge(p, c, role=r["role"], order=r.get("order", 0), year=r["year"])
    return g


def _mode(g: nx.Graph, kind: str) -> list[str]:
    return [n for n, d in g.nodes(data=True) if d.get("kind") == kind]


def company_projection(g: nx.Graph) -> nx.Graph:
    """Firm-by-firm interlock network, weighted by shared directors."""
    return _project(g, _mode(g, "company"), "company")


def person_projection(g: nx.Graph) -> nx.Graph:
    """Director-by-director co-membership network, weighted by shared boards."""
    return _project(g, _mode(g, "person"), "person")


def _project(g: nx.Graph, nodes: list[str], kind: str) -> nx.Graph:
    out = nx.Graph()
    for n in nodes:
        out.add_node(n, **g.nodes[n])
    shared: dict[tuple[str, str], set[str]] = defaultdict(set)
    for other in g.nodes():
        if g.nodes[other].get("kind") == kind:
            continue
        neigh = sorted(x for x in g.neighbors(other) if g.nodes[x].get("kind") == kind)
        for a, b in combinations(neigh, 2):
            shared[(a, b)].add(other)
    for (a, b), via in shared.items():
        out.add_edge(a, b, weight=len(via), via=";".join(sorted(via)))
    return out


def centralities(g: nx.Graph, weight: str | None = "weight") -> dict[str, dict[str, float]]:
    """Standard centralities, guarded for empty and disconnected graphs."""
    if g.number_of_nodes() == 0:
        return {}
    deg = dict(g.degree())
    wdeg = dict(g.degree(weight=weight)) if weight else deg
    try:
        btw = nx.betweenness_centrality(g, weight=None)
    except Exception:
        btw = {n: 0.0 for n in g}
    try:
        eig = nx.eigenvector_centrality_numpy(g, weight=weight)
    except Exception:
        eig = {n: 0.0 for n in g}
    close = nx.closeness_centrality(g)
    return {
        n: {
            "degree": float(deg.get(n, 0)),
            "weighted_degree": float(wdeg.get(n, 0)),
            "betweenness": float(btw.get(n, 0.0)),
            "eigenvector": float(eig.get(n, 0.0)),
            "closeness": float(close.get(n, 0.0)),
        }
        for n in g.nodes()
    }


def describe(g: nx.Graph) -> dict[str, float]:
    """Wave-level structural summary."""
    n, m = g.number_of_nodes(), g.number_of_edges()
    if n == 0:
        return {"nodes": 0, "edges": 0, "density": 0.0, "components": 0,
                "largest_component": 0, "mean_degree": 0.0}
    comps = list(nx.connected_components(g))
    return {
        "nodes": n,
        "edges": m,
        "density": nx.density(g),
        "components": len(comps),
        "largest_component": max(len(c) for c in comps),
        "largest_component_share": max(len(c) for c in comps) / n,
        "mean_degree": 2 * m / n,
    }


def dynamic_graph(per_year: dict[int, nx.Graph]) -> nx.Graph:
    """Merge waves into one graph carrying per-year presence attributes.

    Nodes and edges gain a ``years`` attribute (a semicolon-joined list) plus a
    boolean ``y<year>`` flag, which is what Gephi's partition/filter panels and
    most R/igraph workflows can actually consume.
    """
    merged = nx.Graph()
    for year, g in sorted(per_year.items()):
        for node, data in g.nodes(data=True):
            if node not in merged:
                merged.add_node(node, **{k: v for k, v in data.items()})
                merged.nodes[node]["years"] = []
            merged.nodes[node]["years"].append(year)
            merged.nodes[node][f"y{year}"] = True
        for a, b, data in g.edges(data=True):
            if not merged.has_edge(a, b):
                merged.add_edge(a, b, **{k: v for k, v in data.items() if k != "year"})
                merged[a][b]["years"] = []
            merged[a][b]["years"].append(year)
            merged[a][b][f"y{year}"] = True
    for _, d in merged.nodes(data=True):
        d["years"] = ";".join(str(y) for y in d["years"])
    for _, _, d in merged.edges(data=True):
        d["years"] = ";".join(str(y) for y in d["years"])
    return merged
