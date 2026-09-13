"""Panel of two-mode networks for a temporal ERGM, and its design constraints.

A TERGM is estimable on this dataset, but three properties of it decide the
specification, and every one of them is a reason to narrow the claim rather
than widen it.

**The model must be fitted to the two-mode network.** Not to a projection. A
one-mode projection of an affiliation network manufactures a clique out of
every board, so its triangles and its clustering are arithmetic rather than
behaviour, and the dependence an ERGM is meant to estimate is already baked in
by the construction. Interlocking is represented here by `b2star(2)` — two
directors sharing a firm — on the two-mode graph, which is the same quantity
without the manufactured dependence.

**Node turnover is severe, and the first transition is thin.** A TERGM's
memory term lives on the dyads whose *both* endpoints exist in consecutive
waves. That set is 44 persons × 109 firms across 1932→1938 and 459 × 427
across 1947→1950 — a fortyfold difference. 1932 is also a selection of
prominent administrators rather than a full roster, so the first transition
mixes a change in the annuaire with a change in the network. Every model is
reported with and without it.

**The intervals are unequal — 6, 4, 5 and 3 years.** A TERGM has no offset for
that, so the memory coefficient is an average over four different gaps and is
not a per-year persistence rate. `timecov` lets it vary by transition, which
is the most that can be done here.

One discipline runs through the covariates. **A covariate computed from the
network cannot go on the right-hand side.** Seat counts, financier status and
centrality are all functions of the ties being modelled; including them would
regress the network on itself. Only attributes read off the page are used:
origin (imputed from the name), rank and public office on the person side,
sector on the firm side. Office is printed in the same entry as the
directorships, so it is contemporaneous and stays associational.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

#: Roles that count as a board seat, as in `network.BOARD_ROLES`.
from .network import BOARD_ROLES

#: Terms in the specification, and what each one is for.
SPECIFICATION = """\
edges                      baseline density
memory(autoregression)     a seat held at t-1, held again at t
b1star(2)                  a director holding two seats
b2star(2)                  two directors sharing a firm — interlocking
b1factor(office)           office holders' propensity to hold seats
b1factor(rank)             Pasha and Bey
b1nodematch(origin)        directors sharing a board with their own community
b2factor(sector)           finance, land, agriculture against the rest
"""


def network_panel(processed: Path | None = None,
                  drop_1932: bool = False) -> dict:
    """Edges, node sets and node attributes for each wave.

    Returns a dict with `waves`, `edges` (one frame per wave), `persons` and
    `firms` (attribute frames per wave). Only board roles are kept, and only
    records that pass `origin.is_person`.
    """
    from . import config
    from .origin import is_person
    from .sectors import sector

    processed = Path(processed) if processed else config.PROCESSED
    aff = pd.read_csv(processed / "affiliations.csv")
    aff = aff[aff.person_label.map(is_person) & aff.role.isin(BOARD_ROLES)]

    offices = processed / "person_political.csv"
    flags = (pd.read_csv(offices)[["year", "person_id", "political"]]
             if offices.exists() else
             pd.DataFrame(columns=["year", "person_id", "political"]))

    coded = _origin_by_person(aff)
    waves = sorted(aff.year.unique())
    if drop_1932:
        waves = [w for w in waves if w != 1932]

    edges, persons, firms = {}, {}, {}
    for year in waves:
        chunk = aff[aff.year == year]
        edges[year] = (chunk[["person_id", "company_id"]]
                       .drop_duplicates().reset_index(drop=True))
        p = (chunk[["person_id", "person_label", "rank"]].drop_duplicates("person_id")
             .merge(coded, on="person_id", how="left")
             .merge(flags[flags.year == year][["person_id", "political"]],
                    on="person_id", how="left"))
        p["political"] = p.political.fillna(False).astype(bool)
        p["origin"] = p.origin.fillna("unknown")
        p["rank"] = p["rank"].fillna("").replace("", "untitled")
        persons[year] = p.sort_values("person_id").reset_index(drop=True)

        f = chunk[["company_id", "company_label"]].drop_duplicates("company_id").copy()
        f["sector"] = f.company_label.map(sector)
        firms[year] = f.sort_values("company_id").reset_index(drop=True)
    return {"waves": waves, "edges": edges, "persons": persons, "firms": firms}


def _origin_by_person(aff: pd.DataFrame) -> pd.DataFrame:
    """One origin per person, from the canonical label.

    Origin is a property of the man, not of the wave, so it is coded once and
    held fixed — a name-based imputation that changed between volumes would be
    a linkage artefact, not a biography.
    """
    from .origin import classify_frame

    labels = aff.drop_duplicates("person_id")[["person_id", "person_label"]]
    coded = classify_frame(labels.person_label.unique())
    return (labels.merge(coded, left_on="person_label", right_on="label",
                         how="left")[["person_id", "origin"]])


def transition_table(panel: dict) -> pd.DataFrame:
    """What each transition has to work with.

    The memory term is estimated on dyads whose both endpoints appear in
    consecutive waves, so this table is the first thing to read before any
    coefficient: it is the model's actual sample size.
    """
    waves = panel["waves"]
    rows = []
    for a, b in zip(waves, waves[1:]):
        pa = set(panel["persons"][a].person_id)
        pb = set(panel["persons"][b].person_id)
        fa = set(panel["firms"][a].company_id)
        fb = set(panel["firms"][b].company_id)
        both_p, both_f = pa & pb, fa & fb
        ea = set(map(tuple, panel["edges"][a].to_numpy()))
        eb = set(map(tuple, panel["edges"][b].to_numpy()))
        at_risk = {(p, f) for p in both_p for f in both_f}
        ea_r = ea & at_risk
        eb_r = eb & at_risk
        rows.append({
            "from": a, "to": b, "gap_years": b - a,
            "persons_both": len(both_p), "firms_both": len(both_f),
            "dyads_at_risk": len(at_risk),
            "edges_from": len(ea_r), "edges_to": len(eb_r),
            "stable": len(ea_r & eb_r),
            "formed": len(eb_r - ea_r), "dissolved": len(ea_r - eb_r),
        })
    return pd.DataFrame(rows)


def export_for_r(panel: dict, outdir: Path) -> list[Path]:
    """Write the panel as CSVs for `scripts/tergm.R`.

    Plain CSV rather than an .RData blob, so the input to the model is
    readable and diffable in the repository.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for kind in ("edges", "persons", "firms"):
        frames = []
        for year in panel["waves"]:
            frame = panel[kind][year].copy()
            frame.insert(0, "year", year)
            frames.append(frame)
        path = outdir / f"tergm_{kind}.csv"
        pd.concat(frames, ignore_index=True).to_csv(path, index=False)
        written.append(path)
    return written


# --- estimation ---------------------------------------------------------------
#
# `btergm`'s default estimator is maximum pseudolikelihood with bootstrapped
# confidence intervals (Desmarais and Cranmer 2012; Leifeld, Cranmer and
# Desmarais 2018). That is a logistic regression on the at-risk dyads with
# each term's change statistic as a regressor, and a bootstrap that resamples
# *nodes* rather than dyads. Both are implemented here so the model can be
# fitted without R, and so the R result has something to be checked against.
#
# What this is not: MCMC-MLE. For that, use `scripts/tergm.R`.

#: Change statistics computed by :func:`change_statistics`, in order.
TERMS = ["edges", "memory", "b1star2", "b2star2", "office", "origin_match",
         "sector_finance", "sector_land_property", "sector_agriculture"]

#: Also computed, but not in the default specification. Pass it to
#: :func:`fit_mple` to ask whether an office holder's seat persists better
#: than anyone else's — which is a different question from whether he holds
#: more seats, and has a different answer. See `docs/TERGM.md`.
INTERACTIONS = ["memory_x_office"]


def change_statistics(panel: dict) -> pd.DataFrame:
    """One row per at-risk dyad per transition, with each term's change stat.

    The change statistic of a term is how much the network statistic moves
    when the dyad is toggled on, holding the rest of the observed network
    fixed — which is exactly what conditioning on the rest of the network
    means, and what makes this a pseudolikelihood rather than a likelihood.

    Only dyads whose both endpoints appear in the wave *and* the one before it
    are included, so `memory` distinguishes "no tie" from "did not exist".
    """
    waves = panel["waves"]
    rows = []
    for previous, current in zip(waves, waves[1:]):
        persons = panel["persons"][current]
        firms = panel["firms"][current]
        prev_p = set(panel["persons"][previous].person_id)
        prev_f = set(panel["firms"][previous].company_id)

        at_risk_p = persons[persons.person_id.isin(prev_p)].reset_index(drop=True)
        at_risk_f = firms[firms.company_id.isin(prev_f)].reset_index(drop=True)
        if at_risk_p.empty or at_risk_f.empty:
            continue

        now = set(map(tuple, panel["edges"][current].to_numpy()))
        before = set(map(tuple, panel["edges"][previous].to_numpy()))

        origin = dict(zip(at_risk_p.person_id, at_risk_p.origin))
        office = dict(zip(at_risk_p.person_id, at_risk_p.political))
        sectors = dict(zip(at_risk_f.company_id, at_risk_f.sector))

        # Degrees and the origin composition of each board, on the observed
        # network at t, restricted to the at-risk node set.
        p_ids = list(at_risk_p.person_id)
        f_ids = list(at_risk_f.company_id)
        p_set, f_set = set(p_ids), set(f_ids)
        p_degree = dict.fromkeys(p_ids, 0)
        f_degree = dict.fromkeys(f_ids, 0)
        board_origins: dict[str, dict[str, int]] = {f: {} for f in f_ids}
        for person, firm in now:
            if person in p_set and firm in f_set:
                p_degree[person] += 1
                f_degree[firm] += 1
                who = origin.get(person, "unknown")
                if who != "unknown":
                    board_origins[firm][who] = board_origins[firm].get(who, 0) + 1

        for person in p_ids:
            ego = origin.get(person, "unknown")
            has_office = bool(office.get(person, False))
            for firm in f_ids:
                tie = (person, firm) in now
                # Degrees excluding the focal tie: the change statistic of a
                # two-star is the partner count the new tie would join.
                deg_p = p_degree[person] - (1 if tie else 0)
                deg_f = f_degree[firm] - (1 if tie else 0)
                same = 0
                if ego != "unknown":
                    same = board_origins[firm].get(ego, 0) - (1 if tie else 0)
                rows.append((
                    current, person, firm, int(tie),
                    1,                                        # edges
                    int((person, firm) in before),            # memory
                    deg_p, deg_f,
                    int(has_office),
                    same,
                    int(sectors.get(firm) == "finance"),
                    int(sectors.get(firm) == "land_property"),
                    int(sectors.get(firm) == "agriculture"),
                    int((person, firm) in before) * int(has_office),
                ))
    return pd.DataFrame(rows, columns=["year", "person_id", "company_id",
                                       "tie", *TERMS, *INTERACTIONS])


def fit_mple(design: pd.DataFrame, terms: list[str] | None = None,
             n_boot: int = 200, seed: int = 20260912) -> pd.DataFrame:
    """Pseudolikelihood fit with a node bootstrap, as `btergm` does by default.

    The bootstrap resamples **directors** with replacement and refits, which
    respects the fact that a director's dyads are not independent of each
    other. Resampling dyads would treat them as if they were and would give
    intervals that are far too narrow.
    """
    import warnings

    import statsmodels.api as sm

    terms = list(terms or TERMS)
    y = design.tie.to_numpy()
    X = design[terms].to_numpy(dtype=float)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = sm.Logit(y, X).fit(disp=0, maxiter=200)

    rng = np.random.default_rng(seed)
    people = design.person_id.to_numpy()
    unique = np.unique(people)
    index: dict[str, np.ndarray] = {p: np.where(people == p)[0] for p in unique}
    draws = np.full((n_boot, len(terms)), np.nan)
    for b in range(n_boot):
        picked = rng.choice(unique, size=unique.size, replace=True)
        rows = np.concatenate([index[p] for p in picked])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                draws[b] = sm.Logit(y[rows], X[rows]).fit(disp=0,
                                                          maxiter=200).params
            except Exception:            # a draw with no variation on a term
                continue

    ok = ~np.isnan(draws).any(axis=1)
    return pd.DataFrame({
        "term": terms,
        "estimate": fit.params,
        "boot_se": np.nanstd(draws[ok], axis=0, ddof=1),
        "lo": np.nanpercentile(draws[ok], 2.5, axis=0),
        "hi": np.nanpercentile(draws[ok], 97.5, axis=0),
        "n_dyads": len(design),
        "n_ties": int(y.sum()),
        "n_boot": int(ok.sum()),
    })


def formation_vs_retention(design: pd.DataFrame, n_boot: int = 100,
                           seed: int = 20260913) -> pd.DataFrame:
    """Split the model into the two processes a cross-section cannot separate.

    A TERGM's whole advantage over a cross-sectional ERGM is that it knows
    which ties are new. Fitting the same terms separately to the dyads that
    were **empty** at t-1 and to those that were **filled** asks two different
    questions: what draws a director onto a board he was not on, and what
    keeps him on one he was.

    `memory` is dropped from both — it is constant within each subset and is
    what defines them.
    """
    terms = [t for t in TERMS if t != "memory"]
    out = []
    for label, subset in (("formation", design[design.memory == 0]),
                          ("retention", design[design.memory == 1])):
        fitted = fit_mple(subset, terms=terms, n_boot=n_boot, seed=seed)
        fitted.insert(0, "process", label)
        out.append(fitted)
    return pd.concat(out, ignore_index=True)
