"""Write the dataset to disk in the formats the analysis tools expect."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pandas as pd

from . import network


def _clean(g: nx.Graph) -> nx.Graph:
    """GEXF/GraphML reject None and non-scalar attribute values."""
    h = g.copy()
    for _, d in h.nodes(data=True):
        for k, v in list(d.items()):
            if v is None:
                d[k] = ""
            elif isinstance(v, (list, tuple, set)):
                d[k] = ";".join(str(x) for x in v)
    for _, _, d in h.edges(data=True):
        for k, v in list(d.items()):
            if v is None:
                d[k] = ""
            elif isinstance(v, (list, tuple, set)):
                d[k] = ";".join(str(x) for x in v)
    return h


def write_graph(g: nx.Graph, stem: Path) -> list[Path]:
    stem.parent.mkdir(parents=True, exist_ok=True)
    h = _clean(g)
    written = []
    for ext, writer in (("gexf", nx.write_gexf), ("graphml", nx.write_graphml)):
        path = stem.with_suffix(f".{ext}")
        writer(h, str(path))
        written.append(path)
    edges = pd.DataFrame([
        {"source": a, "target": b, **{k: v for k, v in d.items()}}
        for a, b, d in h.edges(data=True)
    ])
    ep = stem.with_name(stem.name + "_edges").with_suffix(".csv")
    edges.to_csv(ep, index=False)
    written.append(ep)
    return written


def export_all(tables: dict[str, pd.DataFrame], outdir: Path) -> dict[str, list[str]]:
    """Write tables, per-wave graphs, projections, and a metrics summary."""
    outdir.mkdir(parents=True, exist_ok=True)
    written: dict[str, list[str]] = {"tables": [], "graphs": [], "reports": []}

    for name, df in tables.items():
        p = outdir / f"{name}.csv"
        df.to_csv(p, index=False)
        written["tables"].append(str(p))

    aff = tables["affiliations"]
    if aff.empty:
        return written

    per_year_bip: dict[int, nx.Graph] = {}
    per_year_firm: dict[int, nx.Graph] = {}
    summary_rows = []
    node_metric_rows = []

    for year, chunk in aff.groupby("year"):
        rows = chunk.to_dict("records")
        bip = network.build_bipartite(rows)
        firm = network.company_projection(bip)
        pers = network.person_projection(bip)
        per_year_bip[int(year)] = bip
        per_year_firm[int(year)] = firm

        gdir = outdir / "graphs"
        for label, g in (("affiliation", bip), ("company_interlocks", firm),
                         ("person_comembership", pers)):
            for p in write_graph(g, gdir / f"{label}_{year}"):
                written["graphs"].append(str(p))
            desc = network.describe(g)
            summary_rows.append({"year": int(year), "graph": label, **desc})

        for g, level in ((firm, "company"), (pers, "person")):
            for node, cents in network.centralities(g).items():
                node_metric_rows.append({
                    "year": int(year), "level": level, "node_id": node,
                    "label": g.nodes[node].get("label", ""), **cents,
                })

    pd.DataFrame(summary_rows).to_csv(outdir / "network_summary.csv", index=False)
    written["reports"].append(str(outdir / "network_summary.csv"))
    pd.DataFrame(node_metric_rows).to_csv(outdir / "node_metrics.csv", index=False)
    written["reports"].append(str(outdir / "node_metrics.csv"))

    if len(per_year_bip) > 1:
        for label, per_year in (("affiliation", per_year_bip),
                                ("company_interlocks", per_year_firm)):
            merged = network.dynamic_graph(per_year)
            for p in write_graph(merged, outdir / "graphs" / f"{label}_pooled"):
                written["graphs"].append(str(p))

    (outdir / "manifest.json").write_text(
        json.dumps(written, indent=2, ensure_ascii=False), encoding="utf-8")
    return written
