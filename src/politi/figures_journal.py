"""The paper's figure set, reproduced for community of origin.

Follows the plotting idiom of the gender/elites manuscript rather than
inventing one: `theme_classic` with a Times-metric serif, no in-figure titles
(captions live in the LaTeX), greyscale with a single accent, filled diamonds
with horizontal error bars for coefficients, a dashed grey rule at zero, and
6.5 x 4 inch PDFs.

Figure-for-figure correspondence with the manuscript:

===========================  ==========================================
manuscript                   here
===========================  ==========================================
A2  diagnostics              ``fig_diagnostics``
A3  baseline coefficients    ``fig_baseline_coef``
A4  log-normal effects       ``fig_lognormal_effects``
A5  ZINB effects             ``fig_zinb_effects``
A6  permutation             ``fig_permutation``
A7  centrality comparison    ``fig_centrality_compare``
A8  quantile regression      ``fig_quantile``
A9  density by group         ``fig_density_origin``
A10 zero centrality          ``fig_zero_centrality``
    Lorenz curves            ``fig_lorenz``
===========================  ==========================================

One figure is added, because the question here is longitudinal where the
manuscript's was cross-sectional: ``fig_coef_by_wave`` runs the A3 coefficient
plot across the five waves.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .positional import REFERENCE

# The manuscript's palette: greys, with firebrick as the single accent.
GREY = {"25": "#404040", "35": "#595959", "50": "#7F7F7F",
        "60": "#999999", "70": "#B3B3B3", "75": "#BFBFBF", "85": "#D9D9D9"}
ACCENT = "#8B1A1A"          # firebrick4
ORIGIN_FILL = {"arab_egyptian": GREY["35"],
               "european": GREY["75"],
               "local_minority": GREY["60"]}
ORIGIN_LABEL = {"arab_egyptian": "Arab / Egyptian",
                "european": "European",
                "local_minority": "Egyptianised minority"}
TERM_LABEL = {
    "european": "European (vs. Arab/Egyptian)",
    "local_minority": "Egyptianised minority (vs. Arab/Egyptian)",
    "degree_z": "Network size (+1 SD)",
    "closeness_z": "Network reach (+1 SD)",
    "clustering_z": "Local density (+1 SD)",
    "max_board_z": "Largest board (+1 SD)",
}


def journal_style() -> None:
    """theme_classic(base_size=11, base_family='Times New Roman')."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
        "font.size": 11,
        "axes.labelsize": 10, "axes.titlesize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "xtick.color": "black", "ytick.color": "black",
        "axes.labelcolor": "black", "text.color": "black",
        "axes.edgecolor": "black", "axes.linewidth": 0.8,
        "legend.fontsize": 8, "legend.frameon": False,
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "savefig.bbox": "tight",
    })


def _classic(ax) -> None:
    """Drop the top and right spines, as theme_classic does."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(direction="out", length=3, width=0.8, colors="black")


def _save(fig, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    fig.savefig(out.with_suffix(".png"), dpi=200)
    plt.close(fig)
    return out


def _coef_dot(ax, y, est, lo, hi) -> None:
    """The manuscript's mark: a filled diamond with a horizontal error bar."""
    ax.errorbar(est, y, xerr=[[est - lo], [hi - est]], fmt="none",
                ecolor="black", elinewidth=0.4, capsize=2.2, zorder=2)
    ax.plot(est, y, marker="D", markersize=5, color="black", zorder=3)


# --- the models the figures draw on -------------------------------------------

def analysis(panel: pd.DataFrame) -> dict:
    """Fit everything the figure set needs, once."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.discrete.count_model import (ZeroInflatedNegativeBinomialP,
                                                  ZeroInflatedPoisson)

    d = panel[panel.origin != "unknown"].copy()
    d["origin"] = d.origin.cat.remove_unused_categories()
    d["year_f"] = d.year.astype(str)
    base = f'C(origin, Treatment("{REFERENCE}"))'
    cl = d.person_id

    X = pd.get_dummies(d.origin, drop_first=True).astype(float)
    X = sm.add_constant(X, has_constant="add")
    y = d.bc_count.values

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = {
            "data": d, "X": X,
            "lm": smf.ols(f"bc_scaled ~ {base}", data=d).fit(
                cov_type="cluster", cov_kwds={"groups": cl}),
            "qp": smf.glm(f"bc_count ~ {base}", data=d,
                          family=sm.families.Poisson()).fit(
                cov_type="cluster", cov_kwds={"groups": cl}, scale="X2"),
            "zip": ZeroInflatedPoisson(y, X, exog_infl=X).fit(disp=0, maxiter=200),
            "zinb": ZeroInflatedNegativeBinomialP(y, X, exog_infl=X).fit(
                disp=0, maxiter=300),
            "log": smf.ols(
                f"bc_log ~ {base} + degree_z + closeness_z + clustering_z + C(year_f)",
                data=d).fit(cov_type="cluster", cov_kwds={"groups": cl}),
        }
    return out


def _term(res, group: str) -> str:
    key = f'[T.{group}]'
    for t in res.params.index:
        if key in str(t):
            return t
    raise KeyError(group)


# --- A3: baseline coefficients -------------------------------------------------

def fig_baseline_coef(fit: dict, out: Path, group: str = "european") -> Path:
    journal_style()
    models = [("Linear", fit["lm"]), ("Quasi-Poisson", fit["qp"])]
    rows = []
    for name, res in models:
        t = _term(res, group)
        ci = res.conf_int().loc[t]
        rows.append((name, res.params[t], ci[0], ci[1]))
    for name, key in (("ZIP", "zip"), ("ZINB", "zinb")):
        # The count component, as tidy_zi() takes coef(m, "count"). The
        # inflation terms carry an 'inflate_' prefix and are not the estimand.
        res = fit[key]
        est, se = res.params[group], res.bse[group]
        rows.append((name, est, est - 1.96 * se, est + 1.96 * se))

    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    for i, (name, est, lo, hi) in enumerate(rows):
        _coef_dot(ax, i, est, lo, hi)
    ax.axvline(0, linestyle="--", color=GREY["50"], linewidth=0.8, zorder=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.invert_yaxis()
    ax.set_xlabel("Coefficient estimate")
    _classic(ax)
    return _save(fig, out)


# --- A4 / A5: effects as percentage change ------------------------------------

def _pct_rows(res, terms) -> list[tuple[str, float, float, float]]:
    rows = []
    for t in res.params.index:
        label = next((TERM_LABEL[k] for k in terms if k in str(t)), None)
        if label is None:
            continue
        ci = res.conf_int().loc[t]
        rows.append((label,
                     (np.exp(res.params[t]) - 1) * 100,
                     (np.exp(ci[0]) - 1) * 100,
                     (np.exp(ci[1]) - 1) * 100))
    return rows


def fig_effects(fit: dict, out: Path, which: str = "log") -> Path:
    journal_style()
    terms = ["european", "local_minority", "degree_z", "closeness_z", "clustering_z"]
    rows = _pct_rows(fit[which], terms)
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    for i, (_, est, lo, hi) in enumerate(rows):
        _coef_dot(ax, i, est, lo, hi)
    ax.axvline(0, linestyle="--", color=GREY["50"], linewidth=0.8, zorder=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.invert_yaxis()
    ax.set_xlabel("Percentage change")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    _classic(ax)
    return _save(fig, out)


# --- A6: permutation -----------------------------------------------------------

def fig_permutation(panel: pd.DataFrame, out: Path, n_perm: int = 20000,
                    seed: int = 42) -> Path:
    """Origin labels permuted within wave, pooling the wave-demeaned outcome.

    Shuffling inside the wave keeps each wave's size and composition fixed, so
    only the assignment of origin moves — the network's own structure is held.
    """
    journal_style()
    rng = np.random.default_rng(seed)
    d = panel[panel.origin.isin(["arab_egyptian", "european"])].copy()
    d["bc_dm"] = d.bc_log - d.groupby("year").bc_log.transform("mean")
    y = d.bc_dm.to_numpy()
    is_eu = (d.origin == "european").to_numpy()
    year = d.year.to_numpy()
    obs = y[is_eu].mean() - y[~is_eu].mean()

    draws = np.empty(n_perm)
    for i in range(n_perm):
        shuffled = np.empty_like(is_eu)
        for yr in np.unique(year):
            m = year == yr
            shuffled[m] = rng.permutation(is_eu[m])
        draws[i] = y[shuffled].mean() - y[~shuffled].mean()
    p = float(np.mean(np.abs(draws) >= abs(obs)))
    ci = np.quantile(draws, [.025, .975])

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    ax.hist(draws, bins=60, density=True, color=GREY["70"], edgecolor="white",
            linewidth=0.4)
    from scipy.stats import gaussian_kde
    xs = np.linspace(draws.min(), draws.max(), 400)
    ax.plot(xs, gaussian_kde(draws)(xs), color="black", linewidth=0.5)
    ax.axvline(obs, linestyle="--", color="black", linewidth=0.6)
    for v in ci:
        ax.axvline(v, linestyle=":", color=GREY["50"], linewidth=0.6)
    ax.set_xlabel("Difference in log betweenness (European − Arab/Egyptian)")
    ax.set_ylabel("Density")
    ax.annotate(f"observed = {obs:.3f}\n$p$ = {p:.3f}",
                xy=(obs, ax.get_ylim()[1] * 0.92),
                xytext=(6, 0), textcoords="offset points",
                fontsize=8, va="top")
    _classic(ax)
    return _save(fig, out)


# --- A7: centrality comparison -------------------------------------------------

def fig_centrality_compare(panel: pd.DataFrame, out: Path,
                           group: str = "european") -> Path:
    """The test that locates a gap in brokerage rather than general marginality."""
    import statsmodels.formula.api as smf

    journal_style()
    d = panel[panel.origin != "unknown"].copy()
    d["origin"] = d.origin.cat.remove_unused_categories()
    for col, z in (("betweenness", "bc_z"), ("degree", "deg_z"),
                   ("closeness", "clo_z"), ("clustering", "clu_z")):
        d[z] = d.groupby("year")[col].transform(
            lambda s: (s - s.mean()) / (s.std(ddof=0) or 1.0))
    base = f'C(origin, Treatment("{REFERENCE}"))'
    rows = []
    for label, z in (("Betweenness", "bc_z"), ("Degree", "deg_z"),
                     ("Closeness", "clo_z"), ("Clustering", "clu_z")):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.ols(f"{z} ~ {base}", data=d).fit(
                cov_type="cluster", cov_kwds={"groups": d.person_id})
        t = _term(m, group)
        ci = m.conf_int().loc[t]
        rows.append((label, m.params[t], ci[0], ci[1]))

    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    for i, (_, est, lo, hi) in enumerate(rows):
        _coef_dot(ax, i, est, lo, hi)
    ax.axvline(0, linestyle="--", color=GREY["50"], linewidth=0.8, zorder=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.invert_yaxis()
    ax.set_xlabel("Coefficient (SD units)")
    _classic(ax)
    return _save(fig, out)


# --- A8: quantile regression ---------------------------------------------------

def fig_quantile(panel: pd.DataFrame, out: Path, group: str = "european") -> Path:
    """Is the gap constant across the brokerage distribution, or a ceiling?"""
    import statsmodels.formula.api as smf

    journal_style()
    d = panel[(panel.origin != "unknown") & (panel.betweenness > 0)].copy()
    d["origin"] = d.origin.cat.remove_unused_categories()
    base = f'C(origin, Treatment("{REFERENCE}"))'
    taus = [.25, .5, .75, .9, .95]
    rows = []
    for tau in taus:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.quantreg(f"bc_log ~ {base}", data=d).fit(q=tau)
        t = _term(m, group)
        se = m.bse[t]
        rows.append((tau, m.params[t], m.params[t] - 1.96 * se,
                     m.params[t] + 1.96 * se))
    r = pd.DataFrame(rows, columns=["tau", "est", "lo", "hi"])

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    ax.axhline(0, linestyle="--", color=GREY["50"], linewidth=0.8, zorder=1)
    ax.fill_between(r.tau, r.lo, r.hi, color=GREY["85"], alpha=0.55, zorder=2)
    ax.plot(r.tau, r.est, color="black", linewidth=0.6, zorder=3)
    ax.plot(r.tau, r.est, marker="D", markersize=4.5, linestyle="none",
            color="black", zorder=4)
    ax.set_xticks(taus)
    ax.set_xticklabels([f"{int(t*100)}%" for t in taus])
    ax.set_xlabel("Quantile")
    ax.set_ylabel("Coefficient for European")
    _classic(ax)
    return _save(fig, out)


# --- A9: density by group ------------------------------------------------------

def fig_density_origin(panel: pd.DataFrame, out: Path) -> Path:
    from scipy.stats import gaussian_kde

    journal_style()
    d = panel[(panel.origin != "unknown") & (panel.betweenness > 0)]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    for grp in ("arab_egyptian", "european", "local_minority"):
        v = np.log10(d[d.origin == grp].betweenness.to_numpy())
        if v.size < 5 or np.ptp(v) == 0:
            continue
        xs = np.linspace(v.min(), v.max(), 300)
        ax.fill_between(xs, gaussian_kde(v)(xs), color=ORIGIN_FILL[grp],
                        alpha=0.5, linewidth=0, label=ORIGIN_LABEL[grp])
    ax.set_xlabel("Betweenness centrality (log scale)")
    ax.set_ylabel("Density")
    ax.xaxis.set_major_formatter(lambda v, _: f"$10^{{{v:.0f}}}$")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=3)
    _classic(ax)
    return _save(fig, out)


# --- A10: zero centrality ------------------------------------------------------

def fig_zero_centrality(panel: pd.DataFrame, out: Path) -> Path:
    journal_style()
    d = panel[panel.origin != "unknown"]
    stats = (d.groupby("origin", observed=True)
               .agg(n=("betweenness", "size"),
                    n0=("betweenness", lambda s: int((s == 0).sum())))
               .assign(pct=lambda x: x.n0 / x.n * 100).reset_index())
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    for i, r in stats.iterrows():
        ax.bar(i, r.pct, width=0.55, color=ORIGIN_FILL[r.origin])
        ax.text(i, r.pct / 2, f"{r.pct:.1f}%\n({r.n0:,}/{r.n:,})",
                ha="center", va="center", color="white", fontweight="bold",
                fontsize=9)
    ax.set_xticks(range(len(stats)))
    ax.set_xticklabels([ORIGIN_LABEL[o] for o in stats.origin])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Percent with zero centrality")
    _classic(ax)
    return _save(fig, out)


# --- Lorenz curves -------------------------------------------------------------

def _gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, float))
    n = x.size
    if n == 0 or x.sum() == 0:
        return float("nan")
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def fig_lorenz(panel: pd.DataFrame, out: Path) -> Path:
    """Concentration of brokerage within each group, wave by wave."""
    journal_style()
    d = panel[panel.origin != "unknown"]
    years = sorted(d.year.unique())
    fig, axes = plt.subplots(1, len(years), figsize=(6.5 * 1.55, 3.1),
                             sharey=True)
    for ax, year in zip(np.atleast_1d(axes), years):
        chunk = d[d.year == year]
        ax.plot([0, 1], [0, 1], linestyle="--", color=GREY["50"], linewidth=0.4)
        for i, grp in enumerate(("arab_egyptian", "european", "local_minority")):
            v = np.sort(chunk[chunk.origin == grp].betweenness.to_numpy())
            if v.size == 0 or v.sum() == 0:
                continue
            pop = np.arange(1, v.size + 1) / v.size
            val = np.cumsum(v) / v.sum()
            style = {"arab_egyptian": "-", "european": ":", "local_minority": "-."}[grp]
            color = "black" if grp == "arab_egyptian" else (
                ACCENT if grp == "european" else GREY["50"])
            ax.plot(pop, val, linestyle=style, color=color, linewidth=0.85,
                    label=ORIGIN_LABEL[grp] if year == years[0] else None)
            ax.text(0.04, 0.95 - 0.085 * i, f"{_gini(v):.3f}", color=color,
                    fontsize=7.5, va="top", transform=ax.transAxes)
        ax.set_title(str(year), fontsize=10, style="italic")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Cumulative share\nof directors")
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_linewidth(0.5)
        ax.tick_params(direction="out", length=3, colors="black")
    np.atleast_1d(axes)[0].set_ylabel("Cumulative share of betweenness")
    handles, labels = np.atleast_1d(axes)[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.10), fontsize=8)
    fig.subplots_adjust(bottom=0.30)
    fig.text(0.5, -0.02, "Gini coefficients printed per group, in the panel order "
             "of the legend.", fontsize=7.5, color=GREY["25"], ha="center")
    return _save(fig, out)


# --- A2: diagnostics -----------------------------------------------------------

def fig_diagnostics(fit: dict, out: Path) -> Path:
    """Observed vs fitted, residuals vs fitted, and the residual distribution,
    for the log-normal, quasi-Poisson and ZINB fits — the manuscript's check
    that the distributional choice is doing real work."""
    journal_style()
    d = fit["data"]
    fitted = {
        "Log-Normal": np.expm1(fit["log"].fittedvalues),
        "Quasi-Poisson": fit["qp"].fittedvalues,
        "ZINB": fit["zinb"].predict(fit["X"], exog_infl=fit["X"]),
    }
    obs = d.bc_scaled.to_numpy()
    fig, axes = plt.subplots(3, 3, figsize=(9, 8.5))
    for j, (name, f) in enumerate(fitted.items()):
        f = np.asarray(f, dtype=float)
        res = obs - f
        pos = (obs > 0) & (f > 0)

        ax = axes[0, j]
        # A group can have no positive fitted or observed value at all — guard,
        # or the identity line's limits reduce over an empty array.
        if pos.any():
            ax.scatter(f[pos], obs[pos], s=1.4, alpha=0.10, color=GREY["25"],
                       linewidths=0)
            lim = [min(f[pos].min(), obs[pos].min()),
                   max(f[pos].max(), obs[pos].max())]
            ax.plot(lim, lim, linestyle="--", color=GREY["50"], linewidth=0.4)
            ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_title(name, fontsize=10, style="italic")
        if j == 0:
            ax.set_ylabel("Observed")

        ax = axes[1, j]
        if (f > 0).any():
            ax.scatter(f[f > 0], res[f > 0], s=1.4, alpha=0.10,
                       color=GREY["25"], linewidths=0)
            ax.set_xscale("log")
        ax.axhline(0, linestyle="--", color=GREY["50"], linewidth=0.4)
        if j == 0:
            ax.set_ylabel("Residual")

        ax = axes[2, j]
        from scipy.stats import gaussian_kde
        if np.ptp(res) > 0:
            xs = np.linspace(np.percentile(res, 0.5), np.percentile(res, 99.5), 300)
            ax.fill_between(xs, gaussian_kde(res)(xs), color=GREY["75"],
                            edgecolor=GREY["35"], linewidth=0.3, alpha=0.7)
        ax.axvline(0, linestyle="--", color=GREY["50"], linewidth=0.4)
        ax.set_xlabel("Residual")
        if j == 0:
            ax.set_ylabel("Density")

    for ax in axes.flat:
        _classic(ax)
        # ggplot labels only major breaks; on a narrow log range matplotlib
        # labels the minor ticks too and they collide.
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axes[0, 0].text(-0.32, 1.12, "(a) Observed vs. fitted", transform=axes[0, 0].transAxes,
                    fontsize=9, style="italic", ha="left")
    axes[1, 0].text(-0.32, 1.06, "(b) Residuals vs. fitted", transform=axes[1, 0].transAxes,
                    fontsize=9, style="italic", ha="left")
    axes[2, 0].text(-0.32, 1.06, "(c) Residual distribution", transform=axes[2, 0].transAxes,
                    fontsize=9, style="italic", ha="left")
    fig.tight_layout()
    return _save(fig, out)


# --- longitudinal addition -----------------------------------------------------

def fig_coef_by_wave(panel: pd.DataFrame, out: Path) -> Path:
    """A3's coefficient plot, run across the five waves.

    The manuscript's design is cross-sectional; this is the one figure added,
    because the question here is whether the advantage moves over time.
    """
    from .positional import by_wave

    journal_style()
    coefs = by_wave(panel)
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.axvline(0, linestyle="--", color=GREY["50"], linewidth=0.8, zorder=1)
    ypos, labels = [], []
    i = 0
    for year in sorted(coefs.year.unique(), reverse=True):
        for grp in ("local_minority", "european"):
            r = coefs[(coefs.year == year) & (coefs.group == grp)]
            if r.empty:
                continue
            r = r.iloc[0]
            marker = "D" if grp == "european" else "o"
            face = "black" if grp == "european" else "white"
            ax.errorbar(r.coef, i, xerr=[[r.coef - r.lo], [r.hi - r.coef]],
                        fmt="none", ecolor="black", elinewidth=0.4, capsize=2.2)
            ax.plot(r.coef, i, marker=marker, markersize=5, color="black",
                    markerfacecolor=face, markeredgewidth=0.9)
            ypos.append(i)
            labels.append(f"{year}  {'European' if grp == 'european' else 'Minority'}")
            i += 1
        i += 0.6
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Coefficient vs. Arab/Egyptian (log betweenness, net of degree)")
    ax.axvspan(*ax.get_xlim(), ymin=0, ymax=0, color="none")
    _classic(ax)
    return _save(fig, out)


def build_all(panel: pd.DataFrame, outdir: Path, n_perm: int = 20000) -> list[Path]:
    fit = analysis(panel)
    return [
        fig_diagnostics(fit, outdir / "fig_diagnostics.pdf"),
        fig_baseline_coef(fit, outdir / "fig_baseline_coef.pdf"),
        fig_effects(fit, outdir / "fig_lognormal_effects.pdf", which="log"),
        fig_permutation(panel, outdir / "fig_permutation.pdf", n_perm=n_perm),
        fig_centrality_compare(panel, outdir / "fig_centrality_compare.pdf"),
        fig_quantile(panel, outdir / "fig_quantile.pdf"),
        fig_density_origin(panel, outdir / "fig_density_origin.pdf"),
        fig_zero_centrality(panel, outdir / "fig_zero_centrality.pdf"),
        fig_lorenz(panel, outdir / "fig_lorenz.pdf"),
        fig_coef_by_wave(panel, outdir / "fig_coef_by_wave.pdf"),
    ]
