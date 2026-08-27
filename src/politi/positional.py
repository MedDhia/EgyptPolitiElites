"""Positional advantage by community of origin, across the five waves.

Follows the design used for the gender analysis in the Tunisian elite paper,
transposed to origin and extended over time.

* **Outcome**: betweenness centrality — brokerage, the capacity to stand
  between others who are not otherwise connected.
* **Estimand**: the European coefficient with Arab/Egyptian as the reference
  category, so a positive coefficient reads directly as European advantage.
* **Conditioning**: degree, closeness and bipartite clustering. This is what
  makes the claim positional rather than merely about connectedness: it asks
  whether Europeans brokered more *than equally connected Egyptians did*.
* **Distribution**: betweenness is non-negative and heavily zero-inflated, so
  a linear model alone will not do. Four specifications are fitted — linear,
  quasi-Poisson, zero-inflated Poisson, zero-inflated negative binomial.
* **Inference**: standard errors are clustered on the director, because the
  same man appears in up to five waves.
* **The longitudinal part**: origin × wave, which asks whether the advantage
  narrows across the Egyptianisation of the late 1940s.

Centralities are computed **within each wave** and standardised within wave,
since the networks differ in size and raw centrality is not comparable across
them. Betweenness is the normalised form for the same reason.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from . import config, network
from .origin import classify_frame, is_person

REFERENCE = "arab_egyptian"
ORDER = ["arab_egyptian", "european", "local_minority"]


def wave_centralities(affiliations: pd.DataFrame) -> pd.DataFrame:
    """Person-level centrality in each wave's two-mode network.

    Betweenness is measured on the two-mode graph, with firms present as
    nodes: a director's brokerage in this world runs *through* the companies
    he sits on, so removing them would discard the paths being measured.
    """
    rows = []
    for year, chunk in affiliations.groupby("year"):
        g = network.build_bipartite(chunk.to_dict("records"))
        if g.number_of_nodes() == 0:
            continue
        btw = nx.betweenness_centrality(g, normalized=True)
        # Also on the co-membership projection. In the two-mode graph a
        # director holding one seat is a leaf and *must* score zero — brokerage
        # there is geometrically identical to holding two or more seats. The
        # projection lets a one-seat director stand between the colleagues he
        # sits with, so it measures brokerage among people rather than the
        # arithmetic of seat counts.
        proj = network.person_projection(g)
        btw_p = nx.betweenness_centrality(proj, normalized=True)
        deg_p = dict(proj.degree())
        clo = nx.closeness_centrality(g)
        # Ordinary clustering is identically zero on a bipartite graph, which
        # has no triangles; the square (four-cycle) coefficient is its analogue.
        sq = nx.square_clustering(g)
        deg = dict(g.degree())
        for node, attrs in g.nodes(data=True):
            if attrs.get("kind") != "person":
                continue
            rows.append({
                "year": int(year), "person_id": node,
                "person_label": attrs.get("label", ""),
                "betweenness": btw.get(node, 0.0),
                "degree": deg.get(node, 0),
                "closeness": clo.get(node, 0.0),
                "clustering": sq.get(node, 0.0),
                "btw_proj": btw_p.get(node, 0.0),
                "deg_proj": deg_p.get(node, 0),
            })
    return pd.DataFrame(rows)


def build_panel(processed: Path | None = None) -> pd.DataFrame:
    """The person-wave panel the models are fitted on."""
    processed = processed or config.PROCESSED
    aff = pd.read_csv(processed / "affiliations.csv")
    cen = wave_centralities(aff)

    coded = classify_frame(cen.person_label.unique())
    cen = cen.merge(coded, left_on="person_label", right_on="label", how="left")
    cen["is_person"] = cen.person_label.map(is_person)
    cen = cen[cen.is_person].drop(columns=["label", "is_person"])

    # Largest board a director sits on, in this wave. Betweenness in a
    # projected two-mode network rises mechanically with the size of the
    # organisations one belongs to, so this is the artefact control.
    board = aff.groupby(["year", "company_id"]).person_id.nunique().rename("board_size")
    biggest = (aff.merge(board, on=["year", "company_id"])
                  .groupby(["year", "person_id"]).board_size.max()
                  .rename("max_board").reset_index())
    cen = cen.merge(biggest, on=["year", "person_id"], how="left")
    cen["max_board"] = cen.max_board.fillna(1)

    cen["bcp_scaled"] = cen.btw_proj * 1000
    cen["bcp_log"] = np.log1p(cen.bcp_scaled)
    cen["bc_scaled"] = cen.betweenness * 1000
    cen["bc_count"] = cen.bc_scaled.round().astype(int)
    cen["bc_log"] = np.log1p(cen.bc_scaled)

    # Standardise within wave: network size differs, so a raw degree of 6
    # does not mean the same thing in 1932 as in 1950.
    for col in ("degree", "closeness", "clustering", "max_board", "deg_proj"):
        cen[f"{col}_z"] = cen.groupby("year")[col].transform(
            lambda s: (s - s.mean()) / (s.std(ddof=0) or 1.0))

    cen["origin"] = pd.Categorical(cen.origin, categories=ORDER + ["unknown"])
    return cen


# --- models -------------------------------------------------------------------

def _design(df: pd.DataFrame, terms: list[str]) -> tuple[pd.DataFrame, list[str]]:
    import patsy  # noqa: F401  (statsmodels formula backend)
    return df, terms


def fit_models(panel: pd.DataFrame, include_unknown: bool = False) -> dict:
    """Baseline and extended specifications, clustered on the director."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.discrete.count_model import (ZeroInflatedNegativeBinomialP,
                                                  ZeroInflatedPoisson)

    df = panel if include_unknown else panel[panel.origin != "unknown"]
    df = df.copy()
    df["origin"] = df.origin.cat.remove_unused_categories()
    df["year_f"] = df.year.astype(str)
    cl = df.person_id

    out: dict = {}
    base = f'C(origin, Treatment("{REFERENCE}"))'
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out["linear"] = smf.ols(f"bc_scaled ~ {base}", data=df).fit(
            cov_type="cluster", cov_kwds={"groups": cl})
        out["quasipoisson"] = smf.glm(
            f"bc_count ~ {base}", data=df,
            family=sm.families.Poisson()).fit(cov_type="cluster",
                                              cov_kwds={"groups": cl}, scale="X2")
        y = df.bc_count.values
        X = pd.get_dummies(df.origin, drop_first=True).astype(float)
        X = sm.add_constant(X, has_constant="add")
        out["zip"] = ZeroInflatedPoisson(y, X, exog_infl=X, inflation="logit").fit(
            disp=0, maxiter=200)
        out["zinb"] = ZeroInflatedNegativeBinomialP(
            y, X, exog_infl=X, inflation="logit").fit(disp=0, maxiter=300)

        ctrl = "degree_z + closeness_z + clustering_z"
        out["log_controls"] = smf.ols(
            f"bc_log ~ {base} + {ctrl} + C(year_f)", data=df).fit(
            cov_type="cluster", cov_kwds={"groups": cl})
        out["log_artefact"] = smf.ols(
            f"bc_log ~ {base} + {ctrl} + max_board_z + C(year_f)", data=df).fit(
            cov_type="cluster", cov_kwds={"groups": cl})
        out["log_interaction"] = smf.ols(
            f"bc_log ~ {base} * C(year_f) + {ctrl}", data=df).fit(
            cov_type="cluster", cov_kwds={"groups": cl})
    out["_data"] = df
    return out


def by_wave(panel: pd.DataFrame, outcome: str = "bcp_log",
            degree_control: str = "deg_proj_z") -> pd.DataFrame:
    """The origin coefficients wave by wave, net of connectedness.

    Defaults to the projection outcome, since two-mode betweenness is
    determined by seat count and cannot separate brokerage from connectedness.
    """
    import statsmodels.formula.api as smf

    df = panel[panel.origin != "unknown"].copy()
    df["origin"] = df.origin.cat.remove_unused_categories()
    base = f'C(origin, Treatment("{REFERENCE}"))'
    rows = []
    for year, chunk in df.groupby("year"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.ols(f"{outcome} ~ {base} + {degree_control}",
                        data=chunk).fit(cov_type="HC1")
        for grp in ("european", "local_minority"):
            term = f'{base}[T.{grp}]'
            if term not in m.params.index:
                continue
            ci = m.conf_int().loc[term]
            rows.append({"year": int(year), "group": grp,
                         "coef": m.params[term], "se": m.bse[term],
                         "lo": ci[0], "hi": ci[1], "p": m.pvalues[term],
                         "n": int(chunk.shape[0])})
    return pd.DataFrame(rows)


def permutation_test(panel: pd.DataFrame, n_perm: int = 20000,
                     seed: int = 42) -> pd.DataFrame:
    """Within-wave permutation of origin labels.

    Origin is shuffled *inside* each wave, so the null preserves both the
    wave's size and its composition and only the assignment of origin moves.
    """
    rng = np.random.default_rng(seed)
    df = panel[panel.origin.isin(["arab_egyptian", "european"])]
    rows = []
    for year, chunk in df.groupby("year"):
        y = chunk.bc_log.to_numpy()
        is_eu = (chunk.origin == "european").to_numpy()
        if is_eu.sum() < 3 or (~is_eu).sum() < 3:
            continue
        obs = y[is_eu].mean() - y[~is_eu].mean()
        idx = np.arange(len(y))
        draws = np.empty(n_perm)
        for i in range(n_perm):
            rng.shuffle(idx)
            s = is_eu[idx]
            draws[i] = y[s].mean() - y[~s].mean()
        rows.append({"year": int(year), "observed_diff": obs,
                     "p_perm": float(np.mean(np.abs(draws) >= abs(obs))),
                     "null_lo": float(np.quantile(draws, .025)),
                     "null_hi": float(np.quantile(draws, .975)),
                     "d": float(obs / (y.std(ddof=1) or 1.0))})
    return pd.DataFrame(rows)


def concentration(panel: pd.DataFrame) -> pd.DataFrame:
    """Gini of brokerage within each origin group, per wave.

    A group can hold a large share of brokerage while resting it on very few
    men. That fragility is invisible in a mean and is what the Gini exposes.
    """
    def gini(x: np.ndarray) -> float:
        x = np.sort(np.asarray(x, dtype=float))
        n = x.size
        if n == 0 or x.sum() == 0:
            return float("nan")
        return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))

    rows = []
    for (year, grp), chunk in panel[panel.origin != "unknown"].groupby(
            ["year", "origin"], observed=True):
        tot = panel[(panel.year == year) & (panel.origin != "unknown")].betweenness.sum()
        rows.append({"year": int(year), "group": str(grp), "n": len(chunk),
                     "gini": gini(chunk.betweenness.to_numpy()),
                     "share_of_brokerage": (chunk.betweenness.sum() / tot) if tot else np.nan,
                     "share_of_directors": len(chunk) / len(
                         panel[(panel.year == year) & (panel.origin != "unknown")]),
                     "pct_zero": float((chunk.betweenness == 0).mean())})
    return pd.DataFrame(rows)
