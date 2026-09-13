"""Two figures: closure in tie formation, and the brokerage return that isn't.

One file each, as elsewhere. Both figures are built to show the control that
decides the reading rather than only its result — the distance gradient is
printed next to the seat counts that confound it, and the brokerage
coefficients are printed before and after contact volume enters the model.
Reporting only the second of each pair would be reporting a conclusion and
hiding the argument for it.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .explore import AQUA, BLUE, GRID, ORANGE, _caption, _frame, _save
from .viz import INK, INK_SOFT, SURFACE, _style

CLOSURE_FORM_LABEL = {
    "closure": "Count of shared\nprior board-mates",
    "closure_any": "Any shared prior\nboard-mate",
    "closure_log": "log(1 + count)",
    "closure4": "Four-cycles, with\nmultiplicity",
}

BROKERAGE_LABEL = {
    "open_share": "Share of his board-mate\npairs who share no board",
    "effective_size": "Burt's effective size",
    "constraint": "Burt's constraint",
    "mates": "Board-mates (contact volume)",
}

LAG_NOTE = ("Everything on the right-hand side is measured in the previous "
            "volume and the tie in the current one, so the order is clean. "
            "A lag is not an instrument: nothing rules out a third thing "
            "producing both the prior board-mate and the new seat. Read "
            "these as associations.")


def fig_closure(distance: pd.DataFrame, fits: pd.DataFrame,
                stratified: dict, out: Path) -> Path:
    """Embeddedness: the distance gradient, its confound, and the estimates.

    Left panel carries the raw gradient *and* the mean seat count behind each
    band, because the gradient on its own is partly a statement about how many
    boards these men sat on. Right panel is the gradient after both factors of
    the closure count are held fixed.
    """
    _style()
    order = ["3 (a board-mate sits on it)", "5 (two steps out)",
             "7 or more", "unreachable"]
    short = ["3\na board-mate\nsits on it", "5\ntwo steps\nout", "7 or\nmore",
             "unreachable"]
    d = distance.set_index("band").reindex(order)
    # The counts go in the tick labels, not inside the bars: three of the four
    # bars are too short to hold two lines of text.
    short = [f"{lab}\n{int(r.formed)} / {int(r.dyads):,}\n{r.prior_seats:.1f} seats"
             for lab, r in zip(short, d.itertuples())]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.5, 6.4),
                                  gridspec_kw={"width_ratios": [1, 1.15]})

    colours = [BLUE, "#6b9bd8", "#9dc0e8", "#c9cbc4"]
    bars = ax.bar(range(len(d)), d.rate_per_1000, color=colours, width=0.66,
                  zorder=3)
    for bar, row in zip(bars, d.itertuples()):
        ax.text(bar.get_x() + bar.get_width() / 2, row.rate_per_1000 + 0.32,
                f"{row.rate_per_1000:.1f}", ha="center", va="bottom",
                fontsize=10.5, color=INK, fontweight="bold", zorder=4)
    _frame(ax)
    ax.set_xticks(range(len(d)), short, fontsize=9)
    ax.set_ylabel("New ties per 1,000 dyads at risk")
    ax.set_xlabel("His distance to the firm in the previous volume\n(ties formed / dyads at risk, and his mean seat count)",
                  linespacing=1.7)
    ax.set_title("Raw gradient — and the seat counts behind it",
                 fontsize=11.5, color=INK, loc="left", pad=10)
    ax.set_ylim(0, d.rate_per_1000.max() * 1.18)

    forms = list(CLOSURE_FORM_LABEL)
    f = fits[fits.term == fits.form].set_index("form").reindex(forms)
    ypos = np.arange(len(forms))[::-1]
    ax2.axvline(0, color="#b8b5ac", linewidth=1.2, zorder=1)
    for y, (_, r) in zip(ypos, f.iterrows()):
        colour = "#c9cbc4" if r.lo <= 0 <= r.hi else ORANGE
        ax2.plot([r.lo, r.hi], [y, y], color=colour, linewidth=2.4, zorder=2,
                 solid_capstyle="round")
        ax2.plot([r.estimate], [y], "D", color=colour, markersize=9,
                 markeredgecolor=SURFACE, markeredgewidth=1.3, zorder=3)
        ax2.text(r.hi + 0.09, y, f"{r.estimate:+.2f}", va="center",
                 fontsize=10, color=INK, fontweight="bold")
    _frame(ax2, xgrid=True)
    ax2.set_yticks(ypos, [CLOSURE_FORM_LABEL[k] for k in forms], fontsize=9.4)
    ax2.set_ylim(-0.6, len(forms) - 0.4)
    ax2.set_xlabel("Log-odds of the tie forming, per unit of the term")
    ax2.set_title("Net of his seats, his board-mates and the board's size",
                  fontsize=11.5, color=INK, loc="left", pad=10)
    ax2.set_xlim(0, max(f.hi) * 1.28)

    ax2.text(0.985, 0.045,
             "Within wave × board-mates × board-size cells:\n"
             f"{stratified['within_cells']:+.3f} against a permutation null of "
             f"[{stratified['null_lo']:+.3f}, {stratified['null_hi']:+.3f}]\n"
             f"{int(stratified['cells'])} cells, p < 0.0005",
             transform=ax2.transAxes, ha="right", va="bottom", fontsize=8.6,
             color=INK_SOFT, linespacing=1.5)

    _caption(fig, "A board carrying one of his board-mates is the one he joins",
             "Egyptian joint-stock directors, 1932–1950. Formation dyads only — "
             "both endpoints present in consecutive volumes, no tie in the "
             "first. 324,889 dyads, 636 new ties. Bootstrapped pseudolikelihood, "
             "100 node resamples; bars show 95% intervals.",
             LAG_NOTE)
    return _save(fig, out, rect=(0, 0.085, 1, 0.87))


def fig_brokerage(regression: pd.DataFrame, out: Path) -> Path:
    """Burt's half: the same measures before and after contact volume.

    The pairing is the figure. Each brokerage measure appears twice, and the
    only difference between the two rows is whether the number of board-mates
    is in the model. Two of the three measures move to zero; the third is
    collinear with volume at r = 0.98 and cannot be separated from it, which
    is stated on the page rather than left to the reader.

    Colour marks the model, never the result. An earlier draft greyed out every
    interval spanning zero, which made the two models indistinguishable in the
    rows where both do — that is, in most of them. Whether an interval clears
    zero is shown by a hollow marker instead.
    """
    _style()
    measures = ["open_share", "effective_size", "constraint"]
    models = (("seats only", BLUE, 0.18),
              ("seats + contact volume", ORANGE, -0.18))
    fig, ax = plt.subplots(figsize=(12.4, 6.0))
    ax.axvline(0, color="#b8b5ac", linewidth=1.2, zorder=1)

    def draw(row, y, colour, weight="normal"):
        spans = row.lo <= 0 <= row.hi
        ax.plot([row.lo, row.hi], [y, y], color=colour, linewidth=2.4,
                zorder=2, solid_capstyle="round",
                alpha=0.55 if spans else 1.0)
        ax.plot([row.coef], [y], "D", markersize=8.5,
                color=SURFACE if spans else colour,
                markeredgecolor=colour, markeredgewidth=2.0, zorder=3)
        p_text = "p<0.001" if row.p < 0.001 else f"p={row.p:.2f}"
        ax.text(row.hi + 0.05, y, f"{row.coef:+.2f}  {p_text}", va="center",
                fontsize=9.2, color=INK if not spans else INK_SOFT,
                fontweight=weight)

    ticks, labels = [], []
    y = 0.0
    for measure in measures:
        for model, colour, offset in models:
            row = regression[(regression.brokerage == measure)
                             & (regression.model == model)
                             & (regression.term == measure)]
            if not row.empty:
                draw(row.iloc[0], y + offset, colour)
        ticks.append(y)
        labels.append(BROKERAGE_LABEL[measure])
        y -= 1.0

    # Contact volume itself: the term that does carry the association.
    volume = regression[(regression.model == "seats + contact volume")
                        & (regression.term == "mates")
                        & (regression.brokerage == "open_share")]
    if not volume.empty:
        y -= 0.3
        draw(volume.iloc[0], y, AQUA, weight="bold")
        ticks.append(y)
        labels.append(BROKERAGE_LABEL["mates"])

    _frame(ax, xgrid=True)
    ax.set_yticks(ticks, labels, fontsize=9.6)
    ax.set_ylim(y - 0.5, 0.5)
    lo = min(regression.lo.min(), 0) - 0.15
    ax.set_xlim(lo, regression.hi.max() + 0.75)
    ax.set_xlabel("Poisson coefficient on seats acquired by the next volume")
    handles = [plt.Line2D([], [], color=BLUE, linewidth=2.6,
                          label="Seat count held fixed"),
               plt.Line2D([], [], color=ORANGE, linewidth=2.6,
                          label="Seat count and contact volume held fixed"),
               plt.Line2D([], [], color=AQUA, linewidth=2.6,
                          label="Contact volume itself"),
               plt.Line2D([], [], color=INK_SOFT, linewidth=0, marker="D",
                          markersize=8, markerfacecolor=SURFACE,
                          markeredgecolor=INK_SOFT, markeredgewidth=2.0,
                          label="Hollow: interval spans zero")]
    ax.legend(handles=handles, frameon=False, fontsize=9, loc="lower left",
              bbox_to_anchor=(0.005, 0.02))

    _caption(fig, "The brokerage return is contact volume, not non-redundancy",
             "Directors holding two or more seats, 560 person-waves, 1932-1947 "
             "with outcomes read in the following volume. Poisson on seats "
             "acquired, cluster-robust by director, wave and seat-count fixed "
             "effects. Burt's claim is that non-redundant contacts pay at a "
             "given number of contacts, so the number of contacts has to be in "
             "the model.",
             "Effective size correlates 0.979 with the raw board-mate count "
             "here, so its interval is uninformative rather than null: in an "
             "affiliation network, where every board is a clique of mutually "
             "redundant alters, effective size is close to a relabelling of "
             "degree. The measures with content independent of volume are the "
             "open-pair share (r = 0.51) and constraint (r = -0.67).")
    return _save(fig, out, rect=(0, 0.105, 1, 0.845))
