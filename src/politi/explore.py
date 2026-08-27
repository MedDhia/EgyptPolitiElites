"""Descriptive figures for exploring the dataset, one file each.

Each function answers one question and writes one PNG. Two measurement facts
shape several of them and are stated on the figures themselves rather than
left to the reader:

* **1932 is a selection.** Its roster is headed "NOMENCLATURE de *quelques*
  Administrateurs" — some administrators — while later volumes list them all.
  Prominent directors are densely connected by construction, so 1932 sits off
  the trend in anything involving seats or connectedness. It is shaded.
* **A firm's directors are those the roster named.** The dataset is built from
  the person-side roster, so the count of directors attached to a firm is the
  number of listed directors who named it, not the size of its board.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .origin import is_person
from .viz import INK, INK_SOFT, SURFACE, _style

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GRID = "#eceae4"
RULE = "#b8b5ac"
SHADE = "#f1efe9"
ORIGIN_COLOR = {"arab_egyptian": BLUE, "european": ORANGE, "local_minority": AQUA}
ORIGIN_LABEL = {"arab_egyptian": "Arab / Egyptian", "european": "European",
                "local_minority": "Egyptianised minority"}


def _frame(ax, *, xgrid: bool = False) -> None:
    ax.grid(axis="x" if xgrid else "y", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d9d7d0")


def _wrap(text: str, width: int) -> str:
    """Wrap each hand-broken line to *width*, so a note cannot run off the page."""
    import textwrap

    return "\n".join("\n".join(textwrap.wrap(line, width)) if line.strip() else line
                     for line in text.split("\n"))


def _caption(fig, title: str, subtitle: str, note: str = "") -> None:
    fig.suptitle(title, fontsize=16, fontweight="bold", color=INK, x=0.012,
                 ha="left", y=0.985)
    # Wrap to the figure's own width: a caption written for a 13.5in panel
    # overflows an 11.5in one.
    width_in = fig.get_size_inches()[0]
    fig.text(0.012, 0.925, _wrap(subtitle, int(width_in * 11.5)), fontsize=10.2,
             color=INK_SOFT, ha="left", va="top", linespacing=1.55)
    if note:
        fig.text(0.012, 0.015, _wrap(note, int(width_in * 13.5)), fontsize=8.6,
                 color=INK_SOFT, ha="left", va="bottom", linespacing=1.5)


def _save(fig, out: Path, rect=(0, 0.06, 1, 0.86)) -> Path:
    fig.tight_layout(rect=rect)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


def _shade_1932(ax, years) -> None:
    """Mark 1932 as built on a different selection rule."""
    ax.axvspan(years[0] - 0.6, years[0] + (years[1] - years[0]) * 0.42,
               color=SHADE, zorder=0)


# --- 1. how many seats a director held ----------------------------------------

def fig_seats_per_director(aff: pd.DataFrame, out: Path) -> Path:
    _style()
    seats = aff.groupby(["year", "person_id"]).company_id.nunique()
    tab = (pd.crosstab(seats.index.get_level_values("year"), seats.clip(upper=5),
                       normalize="index") * 100)
    years = list(tab.index)
    cats = [1, 2, 3, 4, 5]
    labels = ["1 seat", "2", "3", "4", "5 or more"]
    shades = ["#c9d9ef", "#9dbde4", "#6b9bd8", "#3f7cc9", BLUE]

    fig, ax = plt.subplots(figsize=(11.5, 6.0))
    bottom = np.zeros(len(years))
    for cat, lab, col in zip(cats, labels, shades):
        vals = tab[cat].to_numpy() if cat in tab else np.zeros(len(years))
        ax.bar(range(len(years)), vals, bottom=bottom, width=0.62, color=col,
               edgecolor=SURFACE, linewidth=2, label=lab)
        for i, v in enumerate(vals):
            if v > 4:
                ax.text(i, bottom[i] + v / 2, f"{v:.0f}%", ha="center",
                        va="center", fontsize=9.5,
                        color="white" if cat >= 4 else INK)
        bottom += vals
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylim(0, 100)
    ax.set_ylabel("share of directors in the wave")
    ax.legend(frameon=False, fontsize=9.5, loc="upper center",
              bbox_to_anchor=(0.5, -0.06), ncol=5, labelcolor=INK_SOFT)
    _frame(ax)
    _caption(fig, "Most directors held a single seat",
             "Board seats held per director, by wave. A director with one seat cannot broker: in a two-mode network they are a leaf,\n"
             "so the shaded portion above the first band is the whole of the population that can occupy a bridging position.",
             "1932 is a selection of prominent directors (“quelques Administrateurs”), which is why its single-seat share is far lower. "
             "The later waves list directors comprehensively and are comparable with each other.")
    return _save(fig, out, rect=(0, 0.10, 1, 0.86))


# --- 2. how many directors a firm drew ----------------------------------------

def fig_directors_per_firm(aff: pd.DataFrame, out: Path) -> Path:
    _style()
    counts = aff.groupby(["year", "company_id"]).person_id.nunique()
    years = sorted(aff.year.unique())
    fig, ax = plt.subplots(figsize=(11.5, 6.0))
    for i, year in enumerate(years):
        v = counts.loc[year].to_numpy()
        parts = ax.violinplot([v], positions=[i], widths=0.72,
                              showextrema=False, showmedians=False)
        for body in parts["bodies"]:
            body.set_facecolor(BLUE)
            body.set_alpha(0.28)
            body.set_edgecolor("none")
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        ax.vlines(i, q1, q3, color=BLUE, linewidth=5, alpha=0.85)
        ax.plot(i, med, marker="o", markersize=7, color=BLUE,
                markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=4)
        ax.text(i, v.max() + 0.35, f"max {v.max()}", ha="center", fontsize=8.6,
                color=INK_SOFT)
        ax.text(i, -0.9, f"n={len(v):,} firms", ha="center", fontsize=8.6,
                color=INK_SOFT)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylim(-1.6, counts.max() + 1.6)
    ax.set_ylabel("directors recorded for the firm")
    _frame(ax)
    _caption(fig, "Most firms are recorded through a single director",
             "Distribution of directors recorded per firm, by wave. Dot marks the median, bar the interquartile range.",
             "This is not board size. The dataset is built from the person-side roster, so a firm's count is the number of listed "
             "directors who named it — a firm whose board is large but whose members are mostly unlisted appears small here.")
    return _save(fig, out)


# --- 3. elite persistence ------------------------------------------------------

def fig_elite_persistence(aff: pd.DataFrame, out: Path) -> Path:
    _style()
    years = sorted(aff.year.unique())
    rows = []
    for a, b in zip(years, years[1:]):
        cur = set(aff[aff.year == a].person_id)
        nxt = set(aff[aff.year == b].person_id)
        raw = len(cur & nxt) / len(cur)
        gap = b - a
        rows.append({"pair": f"{a}→{b}", "gap": gap, "raw": raw * 100,
                     "annual": raw ** (1 / gap) * 100, "n": len(cur)})
    d = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    x = np.arange(len(d))
    ax.plot(x, d.raw, color=BLUE, linewidth=2.4, marker="o", markersize=9,
            markeredgecolor=SURFACE, markeredgewidth=1.8, zorder=3)
    ax.plot(x, d.annual, color=ORANGE, linewidth=2.4, marker="s", markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=1.8, zorder=3)
    for i, r in d.iterrows():
        ax.annotate(f"{r.raw:.0f}%", (i, r.raw), textcoords="offset points",
                    xytext=(0, -20), ha="center", fontsize=9.5, color=BLUE)
        ax.annotate(f"{r.annual:.0f}%", (i, r.annual), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=9.5, color=ORANGE)
    ax.annotate("Retained to the next wave", (x[-1], d.raw.iloc[-1]),
                xytext=(12, 0), textcoords="offset points", va="center",
                fontsize=10, color=BLUE, fontweight="bold")
    ax.annotate("Same, per year elapsed", (x[-1], d.annual.iloc[-1]),
                xytext=(12, 0), textcoords="offset points", va="center",
                fontsize=10, color=ORANGE, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r.pair}\n({r.gap} years, n={r.n:,})" for _, r in d.iterrows()],
                       fontsize=9.5)
    ax.set_ylim(0, 100)
    ax.set_xlim(-0.4, len(d) - 0.4 + 1.3)
    ax.set_ylabel("share of directors")
    _frame(ax)
    _caption(fig, "Turnover looks like it fell — until the calendar is taken out",
             "Share of one wave's directors who reappear in the next. Blue is the raw share; orange rescales it to a single year,\n"
             "since the gaps between waves are 6, 4, 5 and 3 years.",
             "The raw series doubles across the period. Adjusted for the years elapsed, retention is roughly flat at about four in "
             "five per year, so most of the apparent rise is the waves getting closer together.\n"
             "Persistence also depends on record linkage: a director whose name was matched across waves counts as retained, and "
             "the linkage is probabilistic (docs/EXTRACTION.md).")
    return _save(fig, out, rect=(0, 0.20, 1, 0.86))


# --- 4. who the busiest directors were ----------------------------------------

def fig_top_brokers(aff: pd.DataFrame, panel: pd.DataFrame, out: Path,
                    top: int = 22) -> Path:
    _style()
    origin = (panel.groupby("person_id").origin
              .agg(lambda s: s.dropna().iloc[0] if s.notna().any() else "unknown"))
    d = (aff.groupby(["person_id", "person_label"])
           .agg(firms=("company_id", "nunique"), waves=("year", "nunique"))
           .reset_index())
    d["origin"] = d.person_id.map(origin).fillna("unknown").astype(str)
    d = d.nlargest(top, "firms").sort_values("firms")

    fig, ax = plt.subplots(figsize=(11.5, 8.4))
    colors = [ORIGIN_COLOR.get(o, "#9a978f") for o in d.origin]
    ax.barh(range(len(d)), d.firms, color=colors, height=0.68)
    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(r.firms + 0.4, i, f"{r.firms}  ·  {r.waves} wave{'s' if r.waves > 1 else ''}",
                va="center", fontsize=9, color=INK_SOFT)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d.person_label, fontsize=9.5)
    ax.set_xlabel("distinct firms across all waves")
    ax.set_xlim(0, d.firms.max() * 1.22)
    handles = [plt.Line2D([], [], marker="s", linestyle="none", markersize=9,
                          markerfacecolor=c, markeredgecolor="none", label=l)
               for k, (c, l) in enumerate(
                   [(ORIGIN_COLOR[o], ORIGIN_LABEL[o]) for o in ORIGIN_COLOR]
                   + [("#9a978f", "Unclassified")])]
    ax.legend(handles=handles, frameon=False, fontsize=9.5, loc="lower right",
              labelcolor=INK_SOFT)
    _frame(ax, xgrid=True)
    _caption(fig, "The most connected directors of the period",
             "Directors ranked by the number of distinct firms whose boards they are recorded on, pooled across all five waves.",
             "Pooling across waves favours men who appear in several volumes, so this ranks cumulative reach rather than standing in "
             "any one year. Origin is imputed from the name and carries error (docs/ORIGIN_CODING.md).")
    return _save(fig, out, rect=(0, 0.055, 1, 0.88))


# --- 5. rank ------------------------------------------------------------------

def fig_rank_structure(aff: pd.DataFrame, out: Path) -> Path:
    _style()
    d = aff.copy()
    d["rank_c"] = d["rank"].fillna("").replace("", "untitled")
    people = d.drop_duplicates(["year", "person_id"])
    comp = (pd.crosstab(people.year, people.rank_c, normalize="index") * 100)
    for col in ("pasha", "bey", "untitled"):
        if col not in comp:
            comp[col] = 0.0
    seats = (d.groupby(["year", "person_id"])
               .agg(firms=("company_id", "nunique"), rank_c=("rank_c", "first"))
               .reset_index().groupby(["year", "rank_c"]).firms.mean().unstack())

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.9))
    years = list(comp.index)
    ax = axes[0]
    for name, col, lab in (("pasha", "#1f4e8c", "Pasha"), ("bey", "#6b9bd8", "Bey")):
        ax.plot(years, comp[name], color=col, linewidth=2.4, marker="o",
                markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.7)
        ax.annotate(lab, (years[-1], comp[name].iloc[-1]), xytext=(10, 0),
                    textcoords="offset points", va="center", fontsize=10,
                    color=col, fontweight="bold")
    ax.set_ylim(0, max(comp[["pasha", "bey"]].to_numpy().max() * 1.35, 10))
    ax.set_xticks(years)
    ax.set_ylabel("share of directors holding the rank (%)")
    ax.set_title("Titled directors, by wave", fontsize=12, loc="left", pad=10,
                 color=INK)
    ax.set_xlim(years[0] - 1, years[-1] + 5)
    _frame(ax)

    ax = axes[1]
    order = [c for c in ("pasha", "bey", "untitled") if c in seats]
    width = 0.24
    for k, col in enumerate(order):
        vals = seats[col].reindex(years)
        ax.bar(np.arange(len(years)) + (k - 1) * width, vals, width=width * 0.92,
               color={"pasha": "#1f4e8c", "bey": "#6b9bd8",
                      "untitled": "#c9d9ef"}[col],
               label={"pasha": "Pasha", "bey": "Bey", "untitled": "Untitled"}[col])
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.set_ylabel("mean seats held")
    ax.set_title("Seats held, by rank", fontsize=12, loc="left", pad=10, color=INK)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=INK_SOFT)
    _frame(ax)

    _caption(fig, "Ottoman-Egyptian rank on Egyptian boards",
             "Pasha and Bey were civil ranks, abolished in 1953. Left: the share of directors holding each. Right: how many seats\n"
             "the titled held relative to the untitled.",
             "Rank is recorded as printed in each volume, so a promotion appears at the next wave rather than when it happened. "
             "Rank was held across every community here and is not a proxy for origin.")
    return _save(fig, out, rect=(0, 0.115, 1, 0.85))


# --- 6. homophily on boards ----------------------------------------------------

def fig_board_homophily(aff: pd.DataFrame, panel: pd.DataFrame, out: Path,
                        n_perm: int = 400, seed: int = 1) -> Path:
    """Did directors sit with their own community more than chance implies?

    The observed share of same-origin pairs cannot be read on its own: as the
    composition of the elite shifts, same-origin pairing changes mechanically.
    The comparison is against origin labels permuted across directors within
    the wave, holding board sizes fixed.
    """
    _style()
    rng = np.random.default_rng(seed)
    m = aff.merge(panel[["year", "person_id", "origin"]],
                  on=["year", "person_id"], how="left")
    m = m[m.origin.notna() & (m.origin != "unknown")]

    def same_share(boards):
        s = t = 0
        for b in boards:
            for x, z in itertools.combinations(b, 2):
                s += x == z
                t += 1
        return s / t if t else np.nan

    rows = []
    for year, chunk in m.groupby("year"):
        boards = [g.drop_duplicates("person_id").origin.tolist()
                  for _, g in chunk.groupby("company_id")]
        boards = [b for b in boards if len(b) > 1]
        if not boards:
            continue
        obs = same_share(boards)
        pool = np.array([x for b in boards for x in b])
        draws = np.empty(n_perm)
        for i in range(n_perm):
            sh = rng.permutation(pool)
            j = 0
            nb = []
            for b in boards:
                nb.append(list(sh[j:j + len(b)]))
                j += len(b)
            draws[i] = same_share(nb)
        rows.append({"year": int(year), "observed": obs * 100,
                     "expected": draws.mean() * 100,
                     "lo": np.quantile(draws, .025) * 100,
                     "hi": np.quantile(draws, .975) * 100,
                     "p": float(np.mean(draws >= obs)),
                     "pairs": sum(len(b) * (len(b) - 1) // 2 for b in boards)})
    d = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    ax.fill_between(d.year, d.lo, d.hi, color=RULE, alpha=0.35, zorder=1,
                    label="Random mixing (95% of draws)")
    ax.plot(d.year, d.expected, color=INK_SOFT, linewidth=1.6, linestyle="--",
            zorder=2, label="Expected under random mixing")
    ax.fill_between(d.year, d.expected, d.observed, color=ORANGE, alpha=0.18,
                    zorder=2)
    ax.plot(d.year, d.observed, color=ORANGE, linewidth=2.6, marker="o",
            markersize=9, markeredgecolor=SURFACE, markeredgewidth=1.8, zorder=4,
            label="Observed")
    for _, r in d.iterrows():
        ax.annotate(f"+{r.observed - r.expected:.0f} pts", (r.year, r.observed),
                    xytext=(0, 13), textcoords="offset points", ha="center",
                    fontsize=9.5, color=ORANGE)
    ax.set_xticks(d.year)
    ax.set_ylim(0, max(d.observed.max() * 1.35, 70))
    ax.set_ylabel("board pairs sharing a community of origin (%)")
    ax.legend(frameon=False, fontsize=9.5, loc="lower right", labelcolor=INK_SOFT)
    _frame(ax)
    _caption(fig, "Directors sat with their own community more than chance implies",
             "Share of co-director pairs sharing an origin, against a null in which origin labels are permuted across directors\n"
             "within the wave, holding board sizes fixed. The gap is the excess over random mixing.",
             "Every wave exceeds the null (p < 0.005 throughout), so the pattern is not an artefact of the elite's changing "
             "composition — a shift toward one group raises same-origin pairing mechanically, and the null already contains that.\n"
             "Pairs are counted only among directors whose origin could be imputed.")
    return _save(fig, out, rect=(0, 0.145, 1, 0.86))


# --- 7. firm turnover ---------------------------------------------------------

def fig_firm_turnover(aff: pd.DataFrame, out: Path) -> Path:
    _style()
    waves = aff.groupby("company_id").year.nunique().value_counts().sort_index()
    years = sorted(aff.year.unique())
    seen: set = set()
    flows = []
    for y in years:
        now = set(aff[aff.year == y].company_id)
        flows.append({"year": y, "new": len(now - seen), "returning": len(now & seen)})
        seen |= now
    f = pd.DataFrame(flows)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.9))
    ax = axes[0]
    ax.bar(waves.index, waves.values, color=BLUE, width=0.6)
    for k, v in waves.items():
        ax.text(k, v + waves.max() * 0.02, f"{v:,}", ha="center", fontsize=9.5,
                color=INK_SOFT)
    ax.set_xticks(list(waves.index))
    ax.set_xlabel("number of waves in which the firm appears")
    ax.set_ylabel("firms")
    ax.set_ylim(0, waves.max() * 1.16)
    ax.set_title("Most firms appear once", fontsize=12, loc="left", pad=10,
                 color=INK)
    _frame(ax)

    ax = axes[1]
    x = np.arange(len(f))
    ax.bar(x, f.returning, width=0.6, color=BLUE, label="Seen in an earlier wave")
    ax.bar(x, f["new"], bottom=f.returning, width=0.6, color="#c9d9ef",
           label="First appearance")
    for i, r in f.iterrows():
        tot = r.returning + r["new"]
        ax.text(i, tot + f[["returning", "new"]].sum(axis=1).max() * 0.02,
                f"{r['new'] / tot:.0%} new", ha="center", fontsize=9.5,
                color=INK_SOFT)
    ax.set_xticks(x)
    ax.set_xticklabels(f.year)
    ax.set_ylabel("firms recorded in the wave")
    ax.set_title("Composition of each wave", fontsize=12, loc="left", pad=10,
                 color=INK)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left", labelcolor=INK_SOFT)
    _frame(ax)

    _caption(fig, "Firms pass through the register; few stay in it",
             "Left: how many waves each firm appears in. Right: how much of each wave is a firm not recorded before.",
             "A firm absent from a wave need not have ceased trading — it may simply have had no director listed in that volume's "
             "roster. These are appearance rates in the source, not founding and failure rates.")
    return _save(fig, out, rect=(0, 0.115, 1, 0.85))


def real_directors(aff: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose 'director' is not a person.

    The roster prints decorations, offices and places beside names, and a few
    were captured as entries. Left in, they rank among the most connected
    'directors' of the period — "Grand Officier Couronne Belge" on seventeen
    boards — which is why every figure here filters first.
    """
    return aff[aff.person_label.map(is_person)].copy()


def build_all(processed: Path, outdir: Path) -> list[Path]:
    aff = real_directors(pd.read_csv(processed / "affiliations.csv"))
    panel_path = processed / "origin_panel.csv"
    panel = (pd.read_csv(panel_path) if panel_path.exists()
             else pd.DataFrame(columns=["year", "person_id", "origin"]))
    made = [
        fig_seats_per_director(aff, outdir / "seats_per_director.png"),
        fig_directors_per_firm(aff, outdir / "directors_per_firm.png"),
        fig_elite_persistence(aff, outdir / "elite_persistence.png"),
        fig_rank_structure(aff, outdir / "rank_structure.png"),
        fig_firm_turnover(aff, outdir / "firm_turnover.png"),
    ]
    if not panel.empty:
        made += [
            fig_top_brokers(aff, panel, outdir / "top_brokers.png"),
            fig_board_homophily(aff, panel, outdir / "board_homophily.png"),
        ]
    return made
