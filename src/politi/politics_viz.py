"""Figures on political connection, one file each.

Every figure here rests on offices Politi chose to print, so all of them carry
the same caveat and several state it on the page: **the coding is a floor.** A
director with no office recorded may have held one the annuaire did not print.
Rates are therefore lower bounds, and movement across waves is movement in the
annuaire's practice as much as in who sat on boards.

The one comparison that survives that caveat is *within* a wave: whoever Politi
recorded as an office holder is compared with everyone else in the same volume,
under the same editorial practice.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .explore import (AQUA, BLUE, GRID, ORANGE, ORIGIN_COLOR, ORIGIN_LABEL,
                      _caption, _frame, _save, real_directors)
from .origin import is_person
from .politics import (OFFICE_LABEL, OFFICES, office_by_wave, origin_with_political,
                       political_panel)
from .viz import INK, INK_SOFT, SURFACE, _dodge_labels, _style

#: Ordered for reading, densest office first.
OFFICE_ORDER = ["parliament", "cabinet", "judicial", "municipal",
                "diplomatic", "provincial", "court"]

OFFICE_COLOR = {
    "parliament": "#1f4e8c", "cabinet": "#2a78d6", "judicial": "#6b9bd8",
    "municipal": "#9dc0e8", "diplomatic": "#eb6834", "provincial": "#f2a07a",
    "court": "#1baf7a",
}

FLOOR_NOTE = ("Politi printed an office when he had it, so these are lower "
              "bounds: a director with none recorded may still have held one. "
              "Read movement across waves as movement in the annuaire's "
              "practice as much as in the boardroom.")


def _directors_per_wave(aff: pd.DataFrame) -> pd.Series:
    return aff.groupby("year").person_id.nunique()


# --- 1. how many directors held office ----------------------------------------

def fig_office_holders(aff: pd.DataFrame, flags: pd.DataFrame, out: Path) -> Path:
    _style()
    total = _directors_per_wave(aff)
    held = flags[flags.political].drop_duplicates(["year", "person_id"])
    counts = pd.DataFrame({o: held.groupby("year")[o].sum() for o in OFFICE_ORDER
                           if o in held}).reindex(total.index).fillna(0)
    share = counts.div(total, axis=0) * 100

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))
    years = [str(y) for y in total.index]

    ax = axes[0]
    bottom = np.zeros(len(total))
    for office in OFFICE_ORDER:
        if office not in share or share[office].sum() == 0:
            continue
        ax.bar(years, share[office], bottom=bottom, width=0.62,
               color=OFFICE_COLOR[office], label=OFFICE_LABEL[office])
        bottom += share[office].to_numpy()
    for x, (y, n) in enumerate(zip(bottom, held.groupby("year").size())):
        ax.annotate(f"{n}", (x, y), xytext=(0, 6), textcoords="offset points",
                    ha="center", fontsize=9.5, color=INK_SOFT)
    ax.set_ylim(0, bottom.max() * 1.18)
    ax.set_ylabel("share of the wave's directors (%)")
    ax.set_title("Directors holding a public office", fontsize=12, color=INK,
                 loc="left", pad=12)
    # Six offices will not fit beside a stack this short, so the key sits
    # under the panel rather than over the 1932 bar.
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT, ncol=3,
              loc="upper center", bbox_to_anchor=(0.5, -0.09), handlelength=1.1,
              columnspacing=1.4)
    _frame(ax)

    ax = axes[1]
    former = (flags.groupby("year").all_former.mean() * 100).reindex(total.index)
    ax.bar(years, 100 - former, width=0.62, color=BLUE, label="Office held at the time")
    ax.bar(years, former, bottom=100 - former, width=0.62, color="#c9d7e8",
           label="Every office printed as past")
    for x, v in enumerate(former):
        ax.annotate(f"{v:.0f}%", (x, 100 - v / 2), ha="center", va="center",
                    fontsize=10, color=INK_SOFT)
    ax.set_ylim(0, 100)
    ax.set_ylabel("share of office holders (%)")
    ax.set_title("Serving, or out of office", fontsize=12, color=INK,
                 loc="left", pad=12)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT, ncol=2,
              loc="upper center", bbox_to_anchor=(0.5, -0.09), handlelength=1.1,
              columnspacing=1.4)
    _frame(ax)

    _caption(fig, "One director in sixteen held a public office",
             "Left: the share of each wave's directors recorded in a public office, by office. Right: whether the office was\n"
             "current or printed as past — the reason the total is not a count of serving officials.",
             FLOOR_NOTE + " A director holding two offices is counted under each, so the bars sum to slightly more than the "
             "share holding any. The number above each bar is the count of directors behind it.")
    return _save(fig, out, rect=(0, 0.155, 1, 0.85))


# --- 2. what office bought: seats ---------------------------------------------

def fig_office_and_seats(aff: pd.DataFrame, flags: pd.DataFrame, out: Path,
                         n_boot: int = 2000, seed: int = 7) -> Path:
    _style()
    seats = (aff.groupby(["year", "person_id"]).company_id.nunique()
             .rename("seats").reset_index()
             .merge(flags[["year", "person_id", "political"]],
                    on=["year", "person_id"], how="left"))
    seats["political"] = seats.political.fillna(False)

    rng = np.random.default_rng(seed)
    rows = []
    for (year, pol), chunk in seats.groupby(["year", "political"]):
        v = chunk.seats.to_numpy()
        draws = rng.choice(v, size=(n_boot, v.size), replace=True).mean(axis=1)
        rows.append({"year": int(year), "political": bool(pol), "mean": v.mean(),
                     "lo": np.percentile(draws, 2.5), "hi": np.percentile(draws, 97.5),
                     "n": v.size})
    d = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for pol, colour, label in ((False, "#b8c8d8", "No office recorded"),
                               (True, ORANGE, "Public office recorded")):
        s = d[d.political == pol].sort_values("year")
        ax.errorbar(s.year, s["mean"], yerr=[s["mean"] - s.lo, s.hi - s["mean"]],
                    fmt="o", color=colour, markersize=10, linewidth=2.2,
                    capsize=0, markeredgecolor=SURFACE, markeredgewidth=1.6,
                    zorder=3)
        ax.plot(s.year, s["mean"], color=colour, linewidth=2.2, zorder=2)
        ax.annotate(label, (s.year.iloc[-1], s["mean"].iloc[-1]), xytext=(12, 0),
                    textcoords="offset points", va="center", fontsize=10.5,
                    color=colour, fontweight="bold")
        if pol:
            for _, r in s.iterrows():
                ax.annotate(f"{r['mean']:.1f}", (r.year, r.hi), xytext=(0, 8),
                            textcoords="offset points", ha="center", fontsize=9.5,
                            color=colour)
    ratio = (d[d.political].set_index("year")["mean"]
             / d[~d.political].set_index("year")["mean"])
    for year, r in ratio.items():
        ax.annotate(f"×{r:.1f}", (year, 0.25), ha="center", fontsize=10,
                    color=INK_SOFT)
    ax.set_xticks(sorted(d.year.unique()))
    ax.set_xlim(min(d.year) - 1.5, max(d.year) + 5.5)
    ax.set_ylim(0, max(d.hi) * 1.18)
    ax.set_ylabel("mean board seats held in the wave")
    _frame(ax)
    _caption(fig, "Office holders sat on two to three times as many boards",
             "Mean seats per director, with 95% bootstrap intervals. The multiple beneath each wave is the ratio of the two means.",
             FLOOR_NOTE + "\nThis is a gap in seats, not evidence that office produced them: men were appointed to boards "
             "because they were already prominent, and prominence is what the office records.")
    return _save(fig, out, rect=(0, 0.145, 1, 0.86))


# --- 3. politically connected firms -------------------------------------------

def fig_connected_firms(firm: pd.DataFrame, out: Path) -> Path:
    _style()
    g = (firm.groupby("year")
         .agg(firms=("company_id", "size"), connected=("connected", "sum")))
    g["pct"] = g.connected / g.firms * 100

    size = (firm.assign(bucket=np.where(firm.connected, "connected", "other"))
            .groupby(["year", "bucket"]).n_directors.mean().unstack())

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.9))
    years = [str(y) for y in g.index]

    ax = axes[0]
    ax.bar(years, g.pct, width=0.62, color=AQUA)
    for x, (pct, n) in enumerate(zip(g.pct, g.connected)):
        ax.annotate(f"{pct:.0f}%\n{n} firms", (x, pct), xytext=(0, 6),
                    textcoords="offset points", ha="center", fontsize=9.5,
                    color=INK_SOFT)
    ax.set_ylim(0, max(g.pct) * 1.35)
    ax.set_ylabel("share of the wave's firms (%)")
    ax.set_title("Firms with a politically connected director", fontsize=12,
                 color=INK, loc="left", pad=12)
    _frame(ax)

    ax = axes[1]
    x = np.arange(len(size))
    ax.bar(x - 0.19, size["other"], width=0.36, color="#b8c8d8",
           label="No connected director")
    ax.bar(x + 0.19, size["connected"], width=0.36, color=AQUA,
           label="At least one")
    ax.set_xticks(x, years)
    ax.set_ylabel("mean directors recorded for the firm")
    ax.set_title("Firms with a connection are larger in the register",
                 fontsize=12, color=INK, loc="left", pad=12)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=INK_SOFT)
    _frame(ax)

    _caption(fig, "About a quarter of firms had a politically connected board",
             "Left: firms with at least one director recorded in public office. Right: how many directors those firms are\n"
             "recorded through, against the rest.",
             FLOOR_NOTE + "\nThe right panel is partly mechanical: a firm recorded through more directors has more chances "
             "to have a connected one. It is a statement about the register, not a finding about board size.")
    return _save(fig, out, rect=(0, 0.155, 1, 0.85))


# --- 4. who held office -------------------------------------------------------

def fig_office_by_origin(panel: pd.DataFrame, out: Path) -> Path:
    _style()
    d = panel[panel.origin != "unknown"].copy()
    share = (d.groupby(["year", "origin"], observed=True).political.mean() * 100).unstack()
    pooled = (d.groupby("origin", observed=True).political.mean() * 100)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.9),
                             gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    drawn = [o for o in ORIGIN_COLOR if o in share]
    for origin in drawn:
        ax.plot(share.index, share[origin], color=ORIGIN_COLOR[origin],
                linewidth=2.4, marker="o", markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=1.7)
    ax.set_xticks(list(share.index))
    ax.set_xlim(min(share.index) - 1, max(share.index) + 9)
    ax.set_ylim(0, max(share.max()) * 1.12)
    # The European and minority lines finish two points apart, so the end
    # labels have to be pushed off each other.
    ends = {o: float(share[o].iloc[-1]) for o in drawn}
    for origin, y in _dodge_labels(ax, ends).items():
        ax.annotate(ORIGIN_LABEL[origin], (share.index[-1] + 0.5, y),
                    va="center", fontsize=10, color=ORIGIN_COLOR[origin],
                    fontweight="bold")
    ax.set_ylabel("share holding a public office (%)")
    ax.set_title("By wave", fontsize=12, color=INK, loc="left", pad=12)
    _frame(ax)

    ax = axes[1]
    order = pooled.sort_values(ascending=False)
    ax.barh(range(len(order)), order.to_numpy(), height=0.42,
            color=[ORIGIN_COLOR.get(o, "#b8c8d8") for o in order.index])
    ax.set_yticks(range(len(order)),
                  [ORIGIN_LABEL.get(o, str(o)) for o in order.index])
    ax.invert_yaxis()
    for i, v in enumerate(order):
        ax.annotate(f"{v:.1f}%", (v, i), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=10, color=INK_SOFT)
    ax.set_xlim(0, max(order) * 1.25)
    ax.set_xlabel("share holding a public office (%)")
    ax.set_title("Pooled across waves", fontsize=12, color=INK, loc="left", pad=12)
    _frame(ax, xgrid=True)

    _caption(fig, "Political office was the Egyptian route into the boardroom",
             "Share of directors of each community recorded in a public office. 1932 is a selection of prominent men, which\n"
             "is why the Arab / Egyptian line starts so high.",
             FLOOR_NOTE + "\nOrigin is imputed from the name and carries error (docs/ORIGIN_CODING.md). Directors whose "
             "origin could not be imputed are excluded here.")
    return _save(fig, out, rect=(0, 0.155, 1, 0.85))


# --- 5. what office bought: position ------------------------------------------

def _coef_panel(ax, d: pd.DataFrame, colour: str, label_x: str) -> None:
    y = np.arange(len(d))[::-1]
    ax.axvline(0, color="#b8b5ac", linewidth=1.2, zorder=1)
    ax.errorbar(d.coef, y, xerr=[d.coef - d.lo, d.hi - d.coef], fmt="D",
                color=colour, markersize=9, linewidth=2.0, capsize=0,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=3)
    ax.set_yticks(y, [str(v) for v in d.year])
    ax.set_ylim(-0.7, len(d) - 0.3)
    ax.set_xlabel(label_x)


def fig_office_position(panel: pd.DataFrame, out: Path) -> Path:
    _style()
    total = office_by_wave(panel, degree_control="1").sort_values("year")
    net = office_by_wave(panel).sort_values("year")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.9), sharey=True)
    _coef_panel(axes[0], total, ORANGE, "difference in log brokerage")
    axes[0].set_title("Raw difference", fontsize=12, color=INK, loc="left", pad=12)
    _coef_panel(axes[1], net, BLUE, "difference in log brokerage")
    axes[1].set_title("Net of how many boards they sat on", fontsize=12,
                      color=INK, loc="left", pad=12)
    # One scale across both panels: the point is that the right-hand intervals
    # are shorter and nearer zero, which a per-panel scale would hide.
    lim = max(abs(pd.concat([total, net]).lo.min()),
              abs(pd.concat([total, net]).hi.max())) * 1.35
    for ax, d in zip(axes, (total, net)):
        for i, (_, r) in enumerate(d.iterrows()):
            ax.annotate(f"{r.coef:+.2f}" + ("*" if r.p < 0.05 else ""),
                        (r.hi, len(d) - 1 - i), xytext=(8, 0),
                        textcoords="offset points", va="center", fontsize=9.5,
                        color=INK_SOFT)
        ax.set_xlim(-lim, lim)
        _frame(ax, xgrid=True)

    _caption(fig, "Office bought seats, not a better position per seat",
             "Difference in log projected betweenness between directors with and without a recorded office, by wave. Bars are\n"
             "95% intervals with heteroskedasticity-robust errors; * marks p < 0.05.",
             "Left, office holders broker substantially more. Right, once the number of boards they sit on is held constant "
             "the difference mostly closes — what office is associated with is more seats, not a more central place among "
             "the directors who hold the same number.\n"
             "Associational throughout: men were recruited to boards because they were already prominent, and the office is "
             "a record of that prominence. 1932 is a selection of prominent men and is not comparable with the rest.")
    return _save(fig, out, rect=(0, 0.145, 1, 0.86))


# --- 6. does office explain the origin gap? -----------------------------------

def fig_origin_adjusted(panel: pd.DataFrame, out: Path) -> Path:
    _style()
    d = origin_with_political(panel)
    d = d[d.group == "european"].sort_values("year")

    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    years = sorted(d.year.unique())
    y = np.arange(len(years))[::-1]
    ax.axvline(0, color="#b8b5ac", linewidth=1.2, zorder=1)
    for spec, colour, offset, label in (
            ("without", "#b8c8d8", 0.16, "Origin only"),
            ("with", ORANGE, -0.16, "Origin, holding office constant")):
        s = d[d.spec == spec].set_index("year").reindex(years).reset_index()
        ax.errorbar(s.coef, y + offset, xerr=[s.coef - s.lo, s.hi - s.coef],
                    fmt="D", color=colour, markersize=9, linewidth=2.0,
                    capsize=0, markeredgecolor=SURFACE, markeredgewidth=1.4,
                    zorder=3, label=label)
    ax.set_yticks(y, [str(v) for v in years])
    ax.set_ylim(-0.7, len(years) - 0.3)
    lim = max(abs(d.lo.min()), abs(d.hi.max())) * 1.22
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("European advantage over Arab / Egyptian directors, in log brokerage")
    ax.legend(frameon=False, fontsize=10, labelcolor=INK_SOFT, loc="lower right")
    _frame(ax, xgrid=True)
    _caption(fig, "Office holding does not explain away the origin comparison",
             "The European coefficient from the wave-by-wave model, before and after holding political office constant.\n"
             "Both specifications control for how many boards a director sat on.",
             "If office were the channel by which Arab/Egyptian directors reached brokerage positions, comparing directors "
             "of equal political standing would move the European coefficient up. In the four comparable waves it moves by "
             "one to six hundredths of a log point, in both directions — the origin comparison is essentially unchanged. "
             "Only 1932 shifts materially, downward (0.70 to 0.53), and 1932 is a selection.\n"
             "1932 is a selection of prominent men. Origin is imputed from the name (docs/ORIGIN_CODING.md).")
    return _save(fig, out, rect=(0, 0.145, 1, 0.86))


def build_all(processed: Path, outdir: Path) -> list[Path]:
    aff = real_directors(pd.read_csv(processed / "affiliations.csv"))
    flags = pd.read_csv(processed / "person_political.csv")
    firm = pd.read_csv(processed / "firm_political.csv")
    made = [
        fig_office_holders(aff, flags, outdir / "office_holders.png"),
        fig_office_and_seats(aff, flags, outdir / "office_and_seats.png"),
        fig_connected_firms(firm, outdir / "connected_firms.png"),
    ]
    panel = political_panel(processed)
    made += [
        fig_office_by_origin(panel, outdir / "office_by_origin.png"),
        fig_office_position(panel, outdir / "office_position.png"),
        fig_origin_adjusted(panel, outdir / "origin_adjusted.png"),
    ]
    return made
