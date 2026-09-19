"""The TERGM's goodness of fit, as the three distributions that decide it.

Read with `docs/TERGM.md`. The figure exists because the tabular p-values
btergm reports are not the evidence here: at these counts they have almost no
power, and every panel below is non-significant by that test while two of the
three are visibly wrong. **What decides the fit is whether the simulated range
covers the observed value at all** — a model that never once produced an
observed feature across 400 simulated networks has failed, whatever the
p-value says. So the simulated range is drawn, not just the simulated mean.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .explore import BLUE, ORANGE, _caption, _frame, _save
from .viz import INK, INK_SOFT, SURFACE, _style

#: Panels, in reading order: the two degree distributions the star terms exist
#: to reproduce, then the closure statistic the model has no term for.
PANELS = (
    ("degree_first_mode", "Seats per director", "Directors", 12),
    ("degree_second_mode", "Directors per firm", "Firms", 12),
    ("dyad_wise_shared_partners", "Shared partners per dyad",
     "Dyads (log scale)", 6),
)


def _panel(ax, frame: pd.DataFrame, xlabel: str, ylabel: str, top: int,
           log: bool) -> None:
    d = frame[frame.level <= top].copy()
    x = d.level.to_numpy(dtype=float)
    obs, sim = d["obs: mean"].to_numpy(), d["sim: mean"].to_numpy()
    lo, hi = d["min.1"].to_numpy(), d["max.1"].to_numpy()
    floor = 0.4 if log else 0.0

    ax.vlines(x + 0.14, np.maximum(lo, floor), np.maximum(hi, floor),
              color=ORANGE, linewidth=6, alpha=0.30, zorder=2)
    ax.plot(x + 0.14, np.maximum(sim, floor), "o", color=ORANGE, markersize=6.5,
            markeredgecolor=SURFACE, markeredgewidth=1.1, zorder=3,
            label="Simulated: mean, and full range over 400 networks")
    ax.plot(x - 0.14, np.maximum(obs, floor), "D", color=BLUE, markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=1.1, zorder=4,
            label="Observed")

    # Mark every level where the simulated range misses the observed value:
    # the model never once produced what the annuaire shows.
    missed = obs > hi
    if missed.any():
        ax.plot(x[missed] - 0.14, np.maximum(obs[missed], floor), "D",
                markersize=13, markerfacecolor="none", markeredgecolor=INK,
                markeredgewidth=1.6, zorder=5)
    if log:
        ax.set_yscale("log")
    _frame(ax)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(0, top + 1, 1 if top <= 8 else 2))


def fig_gof(tables: dict[str, pd.DataFrame], out: Path) -> Path:
    """Observed against simulated for the three distributions that matter."""
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(14.2, 5.4))
    for ax, (key, xlabel, ylabel, top) in zip(axes, PANELS):
        _panel(ax, tables[key], xlabel, ylabel, top,
               log=key == "dyad_wise_shared_partners")

    axes[0].set_title("Too many men with no seat, too few with one",
                      fontsize=10.6, color=INK, loc="left", pad=9)
    axes[1].set_title("Boards larger than any that exist",
                      fontsize=10.6, color=INK, loc="left", pad=9)
    axes[2].set_title("Closure the model cannot make",
                      fontsize=10.6, color=INK, loc="left", pad=9)
    axes[0].legend(frameon=False, fontsize=8.6, loc="upper right")

    # The extremes are single counts and invisible at this scale, so they are
    # stated. Both are levels the model reaches and the register does not.
    for ax, frame, label in ((axes[0], tables["degree_first_mode"], "seats"),
                             (axes[1], tables["degree_second_mode"],
                              "board")):
        obs_top = int(frame.level[frame["max"] > 0].max())
        sim_top = int(frame.level[frame["max.1"] > 0].max())
        noun = ("most seats held by one director"
                if label == "seats" else "largest board")
        ax.text(0.97, 0.58, f"{noun}:\n{obs_top} observed, {sim_top} simulated",
                transform=ax.transAxes, ha="right", va="top", fontsize=8.4,
                color=INK_SOFT, linespacing=1.5)
    axes[2].text(0.97, 0.80, "ringed: the simulated range\nnever reached the "
                 "observed value", transform=axes[2].transAxes, ha="right",
                 va="top", fontsize=8.4, color=INK_SOFT, linespacing=1.5)

    _caption(fig, "Where the temporal ERGM fails, and why it was worth checking",
             "100 networks simulated from the fitted model at each of the four "
             "transitions, against the observed networks. Counts are means over "
             "the four transitions; the band is the full range across all 400 "
             "simulated networks.",
             "Every level plotted here is non-significant on btergm's own "
             "Pr(>z), which at these counts has almost no power — the third "
             "panel is off by two orders of magnitude at p = 0.20. The test "
             "that matters is coverage: at three, four and five shared "
             "partners the simulated range never reaches the observed "
             "count, so the model "
             "cannot generate the concentrated closure that "
             "docs/EMBEDDEDNESS.md reports as the largest predictor of tie "
             "formation in this network. It has no term for it.")
    return _save(fig, out, rect=(0, 0.13, 1, 0.845))
