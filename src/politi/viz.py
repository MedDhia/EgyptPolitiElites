"""Figures showing how the affiliation network changes across the five waves.

Two figures, because the data supports two different claims and confusing them
would be the easiest mistake to make here.

``figure_snapshots`` draws the two-mode network itself, one panel per wave plus
a cumulative panel. It shows *shape*: how much of the network is one connected
core and how much is loose dyads.

``figure_structure`` plots only measures that survive a change in coverage.
This matters because the annuaire's director roster grows from 19 printed pages
in 1932 to 79 in 1950, so the raw number of nodes rises for reasons that have
nothing to do with Egyptian capitalism. Panel size therefore is **not** a
finding, and the figure says so on its face.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.lines import Line2D

from . import config, network

# Categorical slots 1 and 2 of the reference palette, validated for all-pairs
# CVD separation at this size (worst ΔE 24.7 protan). Shape carries the same
# distinction, so mode is never colour-alone.
PERSON = "#2a78d6"
COMPANY = "#eb6834"
EDGE = "#c9c7c0"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
SURFACE = "#fcfcfb"


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "text.color": INK,
        "axes.edgecolor": "#d9d7d0",
        "axes.labelcolor": INK_SOFT,
        "xtick.color": INK_SOFT,
        "ytick.color": INK_SOFT,
    })


def wave_graphs(affiliations: pd.DataFrame) -> dict[int, nx.Graph]:
    """One two-mode graph per wave."""
    return {int(year): network.build_bipartite(chunk.to_dict("records"))
            for year, chunk in affiliations.groupby("year")}


def cumulative_graph(affiliations: pd.DataFrame) -> nx.Graph:
    """Every tie ever printed, pooled across waves.

    A person and a firm are joined if they were ever printed together, so this
    is a union of the waves rather than any single year's structure.
    """
    return network.build_bipartite(affiliations.to_dict("records"))


def _layout(g: nx.Graph, seed: int = 7) -> dict:
    """Force layout for a single connected component."""
    return nx.spring_layout(g, seed=seed, iterations=70,
                            k=1.15 / max(1, g.number_of_nodes() ** 0.5))


def draw_bipartite(g: nx.Graph, ax, title: str, seed: int = 7) -> None:
    """Draw a wave's connected core.

    Only the largest connected component is drawn. The rest of the network is
    hundreds of isolated dyads — a director printed with one firm nobody else
    sits on — and drawing them fills the panel with a halo that carries one
    number's worth of information while hiding the structure. That number is
    reported instead, under the panel.
    """
    ax.set_facecolor(SURFACE)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    if g.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "no data", ha="center", va="center",
                transform=ax.transAxes, color=INK_SOFT)
        return

    components = sorted(nx.connected_components(g), key=len, reverse=True)
    core = g.subgraph(components[0])
    pos = _layout(core, seed=seed)

    n = core.number_of_nodes()
    edge_w = 0.55 if n < 300 else (0.35 if n < 900 else 0.22)
    edge_a = 0.75 if n < 300 else (0.5 if n < 900 else 0.35)
    nx.draw_networkx_edges(core, pos, ax=ax, edge_color=EDGE,
                           width=edge_w, alpha=edge_a)

    people = [x for x, d in core.nodes(data=True) if d.get("kind") == "person"]
    firms = [x for x, d in core.nodes(data=True) if d.get("kind") == "company"]
    deg = dict(core.degree())
    base, step = (14, 9) if n < 300 else ((7, 5) if n < 900 else (4, 3))

    def sizes(nodes):
        return [base + step * (deg.get(x, 1) ** 0.8) for x in nodes]

    nx.draw_networkx_nodes(core, pos, nodelist=firms, ax=ax, node_color=COMPANY,
                           node_size=sizes(firms), node_shape="s",
                           linewidths=0, alpha=0.85)
    nx.draw_networkx_nodes(core, pos, nodelist=people, ax=ax, node_color=PERSON,
                           node_size=sizes(people), node_shape="o",
                           linewidths=0, alpha=0.85)
    ax.set_title(title, fontsize=14, fontweight="bold", color=INK, pad=10)
    ax.set_aspect("equal")   # distances are meaningless, but shape should not lie
    ax.margins(0.04)


def _panel_stats(g: nx.Graph) -> str:
    d = network.describe(g)
    people = sum(1 for _, a in g.nodes(data=True) if a.get("kind") == "person")
    firms = d["nodes"] - people
    fragments = d["components"] - 1
    return (f"{people:,} directors · {firms:,} firms · {d['edges']:,} ties\n"
            f"core holds {d['largest_component_share']:.0%} of nodes; "
            f"{fragments:,} fragments outside it")


def figure_snapshots(affiliations: pd.DataFrame, out: Path) -> Path:
    _style()
    waves = wave_graphs(affiliations)
    years = sorted(waves)

    fig, axes = plt.subplots(2, 3, figsize=(17.5, 13.6))
    for ax, year in zip(axes.flat, years):
        g = waves[year]
        ed = config.edition(year)
        draw_bipartite(g, ax, str(year), seed=7)
        ax.text(0.5, -0.012, _panel_stats(g), transform=ax.transAxes,
                ha="center", va="top", fontsize=9.4, color=INK_SOFT,
                linespacing=1.5)
        ax.text(0.5, -0.135, f"{ed.edition}e édition · {ed.place}",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8.2, color=INK_SOFT, style="italic")

    cum = cumulative_graph(affiliations)
    ax = axes.flat[len(years)]
    draw_bipartite(cum, ax, f"Cumulative {years[0]}–{years[-1]}", seed=7)
    ax.text(0.5, -0.012, _panel_stats(cum), transform=ax.transAxes,
            ha="center", va="top", fontsize=9.4, color=INK_SOFT, linespacing=1.5)
    ax.text(0.5, -0.135, "every tie ever printed, pooled",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=8.2, color=INK_SOFT, style="italic")

    handles = [
        Line2D([], [], marker="o", linestyle="none", markersize=8,
               markerfacecolor=PERSON, markeredgecolor="none", label="Director"),
        Line2D([], [], marker="s", linestyle="none", markersize=8,
               markerfacecolor=COMPANY, markeredgecolor="none", label="Firm"),
        Line2D([], [], color=EDGE, linewidth=1.6, label="Board membership"),
    ]
    fig.legend(handles=handles, loc="upper right", frameon=False,
               bbox_to_anchor=(0.992, 0.995), fontsize=11, labelcolor=INK_SOFT)

    fig.suptitle("Egyptian corporate elite: the two-mode affiliation network",
                 fontsize=19, fontweight="bold", color=INK, x=0.010, ha="left",
                 y=0.988)
    fig.text(0.010, 0.952,
             "Each panel shows the connected core — the largest component. "
             "Directors and the joint-stock companies whose boards they sat on.\n"
             "Élie I. Politi, Annuaire des sociétés égyptiennes par actions.",
             fontsize=10.8, color=INK_SOFT, ha="left", va="top", linespacing=1.5)
    fig.text(0.012, 0.012,
             "Panel size is not a finding: the annuaire's director roster grows "
             "from 19 printed pages in 1932 to 79 in 1950, so node counts track "
             "the source's coverage as much as the economy.\n"
             "Node area scales with degree. 1942 is re-OCR'd from page images — "
             "its shipped text layer is corrupt (see docs/EXTRACTION.md).",
             fontsize=8.8, color=INK_SOFT, ha="left", va="bottom")

    fig.tight_layout(rect=(0, 0.042, 1, 0.925), h_pad=9.0, w_pad=1.5)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def figure_structure(affiliations: pd.DataFrame, out: Path) -> Path:
    """Measures that survive a change in coverage, so waves are comparable.

    The 1932 point is drawn hollow throughout. Its roster is headed
    "NOMENCLATURE de *quelques* Administrateurs" — *some* administrators — while
    the later volumes drop "quelques" and 1942 announces a "Liste Complète".
    1932 is therefore a selection of prominent directors, and prominent
    directors are precisely the ones who sit on several boards. Its high
    density is a property of the list, not of Egyptian capitalism, and joining
    it to the rest with a solid line would draw a decline that did not happen.
    """
    _style()
    waves = wave_graphs(affiliations)
    years = sorted(waves)

    rows = []
    for y in years:
        g = waves[y]
        d = network.describe(g)
        firm_g = network.company_projection(g)
        by_person = (affiliations[affiliations.year == y]
                     .groupby("person_id").company_id.nunique())
        rows.append({
            "year": y,
            "share_multi": (by_person > 1).mean(),
            "giant": d["largest_component_share"],
            "mean_deg": d["mean_degree"],
            "firm_mean_deg": network.describe(firm_g)["mean_degree"],
        })
    df = pd.DataFrame(rows)

    panels = [
        ("share_multi", "Directors sitting on more than one board",
         "share of directors", True),
        ("giant", "Network held together in one component",
         "share of nodes in largest component", True),
        ("mean_deg", "Board seats per node (two-mode)", "mean degree", False),
        ("firm_mean_deg", "Interlocks per firm",
         "mean degree, firm projection", False),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(17.5, 5.2))
    for ax, (col, title, ylab, as_pct) in zip(axes, panels):
        comparable = df[df.year > 1932]
        ax.plot(comparable.year, comparable[col], color=PERSON, linewidth=2,
                zorder=2)
        ax.plot(df.year[:2], df[col][:2], color=PERSON, linewidth=1.4,
                linestyle=(0, (3, 3)), zorder=2)
        ax.plot(comparable.year, comparable[col], linestyle="none", marker="o",
                markersize=8, markerfacecolor=PERSON, markeredgecolor=SURFACE,
                markeredgewidth=1.6, zorder=3)
        ax.plot([1932], [df[col].iloc[0]], linestyle="none", marker="o",
                markersize=8, markerfacecolor=SURFACE, markeredgecolor=PERSON,
                markeredgewidth=2, zorder=3)
        for x, v in zip(df.year, df[col]):
            ax.annotate(f"{v:.0%}" if as_pct else f"{v:.1f}", (x, v),
                        textcoords="offset points", xytext=(0, 11),
                        ha="center", fontsize=9, color=INK_SOFT)
        ax.set_title(title, fontsize=11.5, color=INK, pad=12, loc="left")
        ax.set_ylabel(ylab, fontsize=9)
        ax.set_xticks(df.year.tolist())
        ax.set_xticklabels([str(y) for y in df.year], fontsize=9)
        ax.grid(axis="y", color="#eceae4", linewidth=0.9)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        # Zero-based: these are magnitudes, and a truncated axis would turn
        # small differences into cliffs.
        ax.set_ylim(0, df[col].max() * 1.35)

    fig.suptitle("Structure, on measures that survive a change in coverage",
                 fontsize=17, fontweight="bold", color=INK, x=0.008, ha="left",
                 y=0.985)
    fig.text(0.008, 0.935,
             "Counts of directors and firms rise with the annuaire's own growth, so these ratios — not node totals — are what compares across waves.\n"
             "1932 is hollow and joined by a dashed line: its roster is headed \"NOMENCLATURE de quelques Administrateurs\" — some administrators — while later "
             "volumes list them all\n(1942 announces a \"Liste Complète\"). A selection of prominent directors is dense by construction, so the fall after 1932 is the list changing, not the economy.",
             fontsize=9.4, color=INK_SOFT, ha="left", va="top", linespacing=1.6)
    fig.tight_layout(rect=(0, 0, 1, 0.83))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def build_figures(processed: Path | None = None,
                  outdir: Path | None = None) -> list[Path]:
    processed = processed or config.PROCESSED
    outdir = outdir or (config.ROOT / "figures")
    aff = pd.read_csv(processed / "affiliations.csv")
    return [
        figure_snapshots(aff, outdir / "network_snapshots.png"),
        figure_structure(aff, outdir / "network_structure.png"),
    ]
