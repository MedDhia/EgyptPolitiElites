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
from .politics import (OFFICE_LABEL, OFFICES, baseline_connection, life_table,
                       office_by_wave, origin_with_political,
                       persistence_models, persistence_panel,
                       persistence_stratified, political_panel,
                       military_panel, military_position, MILITARY_TIER_LABEL,
                       office_panel, position_by_group,
                       survival_models, survival_panel, survival_ph_test)
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

    _caption(fig, "One director in sixteen is recorded in a public office",
             "Left: the share of each wave's directors recorded in a public office, by office. Right: whether the office was\n"
             "current or printed as past — the reason the total is not a count of serving officials.",
             FLOOR_NOTE + " A director holding two offices is counted under each, so the bars sum to slightly more than the "
             "share holding any. The number above each bar is the count of directors behind it.")
    return _save(fig, out, rect=(0, 0.155, 1, 0.85))


# --- 2. office and seat count -------------------------------------------------

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
    _caption(fig, "Office holders are recorded on two to three times as many boards",
             "Mean seats per director, with 95% bootstrap intervals. The multiple beneath each wave is the ratio of the two means.",
             FLOOR_NOTE + "\nA difference in seats held, and nothing more. Office and directorship are printed in the same "
             "entry, so the two are simultaneous here and neither is shown to precede the other.")
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

    _caption(fig, "About a quarter of firms are recorded with a connected director",
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

    _caption(fig, "Office holding is concentrated among Egyptian directors",
             "Share of directors of each community recorded in a public office. 1932 is a selection of prominent men, which\n"
             "is why the Arab / Egyptian line starts so high.",
             FLOOR_NOTE + "\nOrigin is imputed from the name and carries error (docs/ORIGIN_CODING.md). Directors whose "
             "origin could not be imputed are excluded here.")
    return _save(fig, out, rect=(0, 0.155, 1, 0.85))


# --- 5. office and position ---------------------------------------------------

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

    _caption(fig, "The brokerage gap is a seat-count gap",
             "Difference in log projected betweenness between directors with and without a recorded office, by wave. Bars are\n"
             "95% intervals with heteroskedasticity-robust errors; * marks p < 0.05.",
             "Left, office holders broker substantially more. Right, once the number of boards they sit on is held constant "
             "most of the difference goes — office is associated with more seats, not with a more central place among the "
             "directors holding the same number.\n"
             "Association only, in neither direction: office and board seat are recorded in the same volume, so nothing here "
             "separates a man reaching boards through his standing from one whose standing followed his boards. 1932 is a "
             "selection of prominent men and is not comparable with the rest.")
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
    _caption(fig, "The origin comparison is unchanged by holding office constant",
             "The European coefficient from the wave-by-wave model, before and after holding political office constant.\n"
             "Both specifications control for how many boards a director sat on.",
             "If office were the channel by which Arab/Egyptian directors reached brokerage positions, comparing directors "
             "of equal political standing would move the European coefficient up. In the four comparable waves it moves by "
             "one to six hundredths of a log point, in both directions — the origin comparison is essentially unchanged. "
             "Only 1932 shifts materially, downward (0.70 to 0.53), and 1932 is a selection.\n"
             "1932 is a selection of prominent men. Origin is imputed from the name (docs/ORIGIN_CODING.md).")
    return _save(fig, out, rect=(0, 0.145, 1, 0.86))


# --- 7. do connected firms persist? -------------------------------------------

def fig_firm_persistence(panel: pd.DataFrame, out: Path, n_perm: int = 4000) -> Path:
    """Reappearance in the next volume, before and after the artefact controls.

    The raw gap is large and the controlled one is not, so the figure has to
    show both or it misleads either way.
    """
    _style()
    models = persistence_models(panel)
    strat = persistence_stratified(panel, n_perm=n_perm)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.0),
                             gridspec_kw={"width_ratios": [1.05, 1]})

    # Left: the raw rates that prompt the question, and the composition that
    # accounts for them.
    ax = axes[0]
    rates = (panel.groupby(["year", "connected"]).reappears.mean() * 100).unstack()
    years = [str(y) for y in rates.index]
    x = np.arange(len(rates))
    ax.bar(x - 0.19, rates[False], width=0.36, color="#b8c8d8",
           label="No connected director")
    ax.bar(x + 0.19, rates[True], width=0.36, color=AQUA, label="At least one")
    for i, (a, b) in enumerate(zip(rates[False], rates[True])):
        ax.annotate(f"{a:.0f}", (i - 0.19, a), xytext=(0, 5), ha="center",
                    textcoords="offset points", fontsize=9.5, color=INK_SOFT)
        ax.annotate(f"{b:.0f}", (i + 0.19, b), xytext=(0, 5), ha="center",
                    textcoords="offset points", fontsize=9.5, color=INK_SOFT)
    ax.set_xticks(x, years)
    ax.set_ylim(0, max(rates.max()) * 1.28)
    ax.set_ylabel("firms appearing in the next volume (%)")
    ax.set_title("Raw reappearance rate", fontsize=12, color=INK, loc="left",
                 pad=12)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=INK_SOFT, ncol=2,
              loc="upper center", bbox_to_anchor=(0.5, -0.09), handlelength=1.1)
    _frame(ax)

    # Right: what survives each control.
    ax = axes[1]
    y = np.arange(len(models))[::-1]
    ax.axvline(1, color="#b8b5ac", linewidth=1.2, zorder=1)
    colours = [AQUA if r.p < 0.05 else "#b8c8d8" for _, r in models.iterrows()]
    for i, ((_, r), colour) in enumerate(zip(models.iterrows(), colours)):
        ax.plot([r.lo, r.hi], [y[i], y[i]], color=colour, linewidth=2.4, zorder=2)
        ax.plot([r["or"]], [y[i]], "D", color=colour, markersize=9,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=3)
        ax.annotate(f"{r['or']:.2f}" + ("*" if r.p < 0.05 else ""),
                    (r.hi, y[i]), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=9.5, color=INK_SOFT)
    ax.set_yticks(y, [_wrap_label(c) for c in models.controls])
    ax.set_ylim(-0.7, len(models) - 0.3)
    ax.set_xlim(0.5, max(models.hi) * 1.22)
    ax.set_xlabel("odds ratio for reappearing in the next volume")
    ax.set_title("What survives the controls", fontsize=12, color=INK,
                 loc="left", pad=12)
    _frame(ax, xgrid=True)

    _caption(fig, "The persistence gap is accounted for by how firms are recorded",
             "Left: the share of firms appearing in the next volume. Right: the odds ratio on having a connected director,\n"
             "adding one control at a time; * marks p < 0.05, with firm-clustered errors.",
             "Firms with a connected director are recorded through 2.5 to 2.9 directors against 1.6 to 1.8 for the rest, and a "
             "firm recorded through more directors is far likelier to be recorded again — 30% of one-director firms reappear "
             "against 89% of those with four or more. Holding that constant, the gap goes. Comparing firms only with firms in "
             f"the same wave recorded through the same number of directors leaves {strat['pooled_pts']:+.1f} points "
             f"(permutation p = {strat['p_perm']:.2f}, {strat['n_cells']} cells).\n"
             "This is not evidence of no association: the interval still admits odds a third higher or a fifth lower. And "
             "reappearing in the annuaire is not surviving as a company — a firm can trade on unrecorded.")
    return _save(fig, out, rect=(0, 0.185, 1, 0.85))


def _wrap_label(text: str) -> str:
    """Two lines at most, for a y-axis category."""
    parts = text.split(", ")
    if len(parts) < 3:
        return text
    return ", ".join(parts[:2]) + ",\n" + ", ".join(parts[2:])


# --- 8. survival --------------------------------------------------------------

def fig_survival(panel: pd.DataFrame, out: Path) -> Path:
    """Discrete-time survival in the register, by political connection.

    The survivor curve is stratified on connection *at entry*, because a
    survivor function cannot be stratified on a covariate that moves; the
    model beside it uses the time-varying flag.
    """
    _style()
    d = panel.assign(entry_connected=baseline_connection(panel))
    table = life_table(d, by="entry_connected")
    models = survival_models(panel)
    ph = survival_ph_test(panel)

    fig = plt.figure(figsize=(13.5, 6.6))
    grid = fig.add_gridspec(2, 2, width_ratios=[1, 1.05],
                            height_ratios=[5, 1], hspace=0.06, wspace=0.28)
    ax = fig.add_subplot(grid[0, 0])
    risk_ax = fig.add_subplot(grid[1, 0], sharex=ax)

    # Left: the survivor function, drawn as the step function it is, with the
    # numbers at risk on their own axes so they cannot collide with the plot.
    series = ((False, "#8fa8bf", "Not connected at entry"),
              (True, AQUA, "Connected at entry"))
    ends = {}
    for flag, colour, _ in series:
        s = table[table.entry_connected == flag].sort_values("tenure_cat")
        x = np.concatenate([[0], s.tenure_cat.to_numpy()])
        y = np.concatenate([[1.0], s.survival.to_numpy()]) * 100
        ax.step(x, y, where="post", color=colour, linewidth=2.6, zorder=3)
        ax.plot(x[1:], y[1:], "o", color=colour, markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)
        ends[flag] = float(y[-1])
    ax.set_ylim(0, 100)
    for (flag, colour, label), y in zip(series, _dodge_labels(ax, ends).values()):
        ax.annotate(label, (4.15, y), va="center", fontsize=10, color=colour,
                    fontweight="bold")
    ax.set_xlim(-0.35, 7.6)
    ax.set_ylabel("still recorded (%)")
    ax.set_title("Survivor function in the register", fontsize=12, color=INK,
                 loc="left", pad=12)
    ax.tick_params(labelbottom=False)
    _frame(ax)

    # Rows in the same vertical order as the curves: connected sits higher.
    for i, (flag, colour, _) in enumerate(reversed(series)):
        s = table[table.entry_connected == flag].sort_values("tenure_cat")
        for xi, n in zip(s.tenure_cat, s.at_risk):
            risk_ax.text(xi, 0.62 - i * 0.5, f"{n:,}", ha="center", va="center",
                         fontsize=9, color=colour)
    risk_ax.text(-0.3, 1.12, "firms at risk", ha="left", va="center",
                 fontsize=9, color=INK_SOFT)
    risk_ax.set_ylim(-0.1, 1.25)
    risk_ax.set_yticks([])
    risk_ax.set_xticks(range(5))
    risk_ax.set_xlabel("volumes since the firm was first recorded")
    for side in ("top", "right", "left"):
        risk_ax.spines[side].set_visible(False)
    risk_ax.spines["bottom"].set_color("#d9d7d0")

    # Right: hazard ratios as each artefact control goes in.
    ax = fig.add_subplot(grid[:, 1])
    y = np.arange(len(models))[::-1]
    ax.axvline(1, color="#b8b5ac", linewidth=1.2, zorder=1)
    for i, (_, r) in enumerate(models.iterrows()):
        colour = AQUA if r.p < 0.05 else "#b8c8d8"
        ax.plot([r.lo, r.hi], [y[i], y[i]], color=colour, linewidth=2.4, zorder=2)
        ax.plot([r.hr], [y[i]], "D", color=colour, markersize=9,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=3)
        ax.annotate(f"{r.hr:.2f}" + ("*" if r.p < 0.05 else ""), (r.hi, y[i]),
                    xytext=(8, 0), textcoords="offset points", va="center",
                    fontsize=9.5, color=INK_SOFT)
    ax.set_yticks(y, [_wrap_label(c) for c in models.controls])
    ax.set_ylim(-0.7, len(models) - 0.3)
    ax.set_xlim(0.45, max(models.hi) * 1.2)
    ax.set_xlabel("hazard ratio for leaving the register")
    ax.set_title("Hazard of dropping out", fontsize=12, color=INK, loc="left",
                 pad=12)
    _frame(ax, xgrid=True)

    tenure_p = float(ph.loc[ph.interaction == "tenure", "p"].iloc[0])
    wave_p = float(ph.loc[ph.interaction == "wave", "p"].iloc[0])
    fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.235)
    _caption(fig, "Firms leave the register on a falling hazard, connected or not",
             "Discrete-time hazard model on the firm-wave risk set: complementary log-log with log(interval) as an offset, so\n"
             "the 6-, 4-, 5- and 3-year gaps are comparable and the coefficients read as hazard ratios. Errors clustered on the firm.",
             f"The hazard falls steeply with tenure — {table[table.tenure_cat == 1].events.sum() / table[table.tenure_cat == 1].at_risk.sum() * 100:.0f}% "
             f"of firms recorded once are not recorded in the next volume, against "
             f"{table[table.tenure_cat == 4].events.sum() / table[table.tenure_cat == 4].at_risk.sum() * 100:.0f}% of those recorded four times. "
             "Connection looks protective until the number of directors the register records is held constant, after which it "
             "is not distinguishable from none. The association does not vary with tenure "
             f"(p = {tenure_p:.2f}) or wave (p = {wave_p:.2f}), so one ratio is a fair summary of it.\n"
             "Leaving the register is not failing: the volumes record a firm only through its listed directors, and give no "
             "founding date, so the clock runs from first appearance and not from incorporation.")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=170)
    plt.close(fig)
    return out


# --- 9. military officers -----------------------------------------------------

TIER_COLOR = {"general_officer": "#1f4e8c", "field_officer": "#2a78d6",
              "junior_officer": "#9dc0e8", "service_no_rank": "#c9d7e8"}


def fig_military(panel: pd.DataFrame, out: Path, n_perm: int = 5000) -> Path:
    """Where the directors with a military rank sit, one dot each.

    Nineteen officers hold a board seat across five volumes. That is far too
    few for a model, so the left panel is the roster itself and the right
    panel says how wide the null is.
    """
    _style()
    officers = panel[panel.military].sort_values(
        ["year", "pct_btw_proj"], ascending=[True, True]).reset_index(drop=True)
    test = military_position(panel, n_perm=n_perm)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.6),
                             gridspec_kw={"width_ratios": [1.45, 1]})

    ax = axes[0]
    y = np.arange(len(officers))
    ax.axvline(50, color="#b8b5ac", linewidth=1.2, zorder=1)
    ax.annotate("median director\nof the wave", (50, len(officers) - 0.4),
                xytext=(6, 0), textcoords="offset points", fontsize=8.6,
                color=INK_SOFT, va="top")
    for tier, group in officers.groupby("tier"):
        ax.scatter(group.pct_btw_proj, group.index, s=110, zorder=3,
                   color=TIER_COLOR.get(tier, "#b8c8d8"),
                   edgecolor=SURFACE, linewidth=1.4,
                   label=MILITARY_TIER_LABEL.get(tier, str(tier)))
    labels = [f"{r.person_label[:30]}  ·{int(r.year)}  {int(r.seats)}"
              f"{' seats' if r.seats != 1 else ' seat'}"
              for _, r in officers.iterrows()]
    ax.set_yticks(y, labels, fontsize=8.8)
    ax.set_ylim(-0.8, len(officers) - 0.2)
    ax.set_xlim(0, 108)
    ax.set_xlabel("percentile of brokerage within the wave")
    ax.set_title("Every director with a military rank", fontsize=12, color=INK,
                 loc="left", pad=12)
    # The dots fall in two clumps, near the 40th percentile and above the
    # 85th, leaving a clear band between them for the key.
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT, loc="center",
              bbox_to_anchor=(0.66, 0.46), handlelength=1.0)
    _frame(ax, xgrid=True)

    ax = axes[1]
    names = {"pct_seats": "Board seats", "pct_deg_proj": "Co-directors",
             "pct_btw_proj": "Brokerage"}
    ypos = np.arange(len(test))[::-1]
    ax.axvline(0, color="#b8b5ac", linewidth=1.2, zorder=1)
    for i, (_, r) in enumerate(test.iterrows()):
        ax.plot([r.null_lo, r.null_hi], [ypos[i], ypos[i]], color="#d5d2ca",
                linewidth=9, solid_capstyle="butt", zorder=2)
        ax.plot([r.difference], [ypos[i]], "D", color=BLUE, markersize=10,
                markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
        ax.annotate(f"{r.difference:+.1f}  p={r.p_perm:.2f}",
                    (max(r.null_hi, r.difference), ypos[i]), xytext=(9, 0),
                    textcoords="offset points", va="center", fontsize=9.5,
                    color=INK_SOFT)
    ax.set_yticks(ypos, [names[m] for m in test.measure])
    ax.set_ylim(-0.7, len(test) - 0.3)
    ax.set_xlim(-20, 26)
    ax.set_xlabel("officers' mean percentile minus everyone else's")
    ax.set_title("Against a within-wave null", fontsize=12, color=INK,
                 loc="left", pad=12)
    _frame(ax, xgrid=True)

    ottoman = officers.person_label.str.contains(
        r"Lewa|Miralai|Hamdi Pacha|Susu Pacha", case=False, na=False)
    _caption(fig, "Officers sit in the middle of the network, not at its centre",
             "Left: each director recorded with a military rank, placed by his percentile of brokerage among the directors of\n"
             "his own wave. Right: the officers' mean percentile against a null that redraws the same number inside each wave.",
             f"The grey bars are the middle 95% of that null. Every observed difference falls inside one, so nothing here "
             f"separates officers from the rest — but with {int(test.n.iloc[0])} officers the null is about ±10 percentile "
             "points wide, so this is too few to tell, not a demonstration that they were ordinary.\n"
             f"The {int(ottoman.sum())} men holding Ottoman-Egyptian rank — lewa, miralai — average "
             f"{officers.seats[ottoman].mean():.1f} board seat and the {int((~ottoman).sum())} holding British or European "
             f"commissions average {officers.seats[~ottoman].mean():.1f}. Several of the latter are businessmen with wartime "
             "or honorary commissions rather than career soldiers, which is a caution about reading the group as an "
             "officer corps at all. Rank is coded only where Politi printed it (docs/POLITICAL_CONNECTIONS.md).")
    return _save(fig, out, rect=(0, 0.14, 1, 0.86))


# --- 10. where office holders sit ---------------------------------------------

def fig_office_centrality(panel: pd.DataFrame, out: Path,
                          n_perm: int = 4000) -> Path:
    """The military figure's question, asked of civil office.

    Two measures per office, because they separate: every office goes with
    more board seats, but only some go with a more central position.
    """
    _style()
    groups = [*OFFICES, "political"]
    test = position_by_group(panel, groups, n_perm=n_perm)
    order = (test[test.measure == "pct_btw_proj"]
             .sort_values("difference").group.tolist())
    order = [g for g in order if g != "political"] + ["political"]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.4), sharey=True,
                             gridspec_kw={"width_ratios": [1, 1]})
    labels = {**OFFICE_LABEL, "political": "Any office"}

    for ax, measure, title, colour in (
            (axes[0], "pct_seats", "Board seats held", BLUE),
            (axes[1], "pct_btw_proj", "Brokerage", ORANGE)):
        d = (test[test.measure == measure].set_index("group")
             .reindex(order).reset_index())
        y = np.arange(len(d))[::-1]
        ax.axvline(0, color="#b8b5ac", linewidth=1.2, zorder=1)
        for i, (_, r) in enumerate(d.iterrows()):
            ax.plot([r.null_lo, r.null_hi], [y[i], y[i]], color="#d5d2ca",
                    linewidth=9, solid_capstyle="butt", zorder=2)
            face = colour if r.p_perm < 0.05 else "#b8c8d8"
            ax.plot([r.difference], [y[i]], "D", color=face, markersize=10,
                    markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
            ax.annotate(f"{r.difference:+.0f}" + ("" if r.p_perm < 0.05 else " n.s."),
                        (r.difference, y[i]), xytext=(0, 12),
                        textcoords="offset points", ha="center", fontsize=9.2,
                        color=INK_SOFT)
        ax.set_yticks(y, [f"{labels[g]}  ({int(d.n.iloc[list(d.group).index(g)])})"
                          for g in d.group])
        ax.set_ylim(-0.7, len(d) - 0.25)
        ax.set_xlim(-14, 42)
        ax.set_xlabel("percentile points above the rest of the wave")
        ax.set_title(title, fontsize=12, color=INK, loc="left", pad=12)
        _frame(ax, xgrid=True)
    axes[0].tick_params(labelsize=9.6)

    _caption(fig, "Office goes with more seats everywhere, but not with a central place everywhere",
             "Each office holder's mean percentile within his own wave, minus everyone else's. Grey bars are the middle 95%\n"
             "of a null that redraws the same number of holders inside each wave. Counts of person-waves in brackets.",
             "Every office sits some twenty points above the rest of its wave on seats held. On brokerage they separate: "
             "parliamentarians, diplomats, provincial governors and municipal councillors are well above the rest, while the "
             "bench is not distinguishable from it — judges hold more boards than average but smaller ones, 1.5 co-directors "
             "per seat against 2.2 for directors with no office at all.\n"
             "Read the grey bars before the diamonds: provincial administration has ten person-waves and a null three times "
             "as wide as parliament's. Association only — office and directorship are printed in the same entry, so neither "
             "is shown to precede the other, and offices are coded only where Politi printed them.")
    return _save(fig, out, rect=(0, 0.16, 1, 0.85))


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
        fig_firm_persistence(persistence_panel(processed),
                             outdir / "firm_persistence.png"),
        fig_survival(survival_panel(processed), outdir / "firm_survival.png"),
        fig_military(military_panel(processed), outdir / "military_officers.png"),
        fig_office_centrality(office_panel(processed),
                              outdir / "office_centrality.png"),
    ]
    return made
