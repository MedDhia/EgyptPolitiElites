"""Embeddedness against structural holes, in a two-mode affiliation network.

Two theories of tie formation, both of them claims about *dependence between
ties* and therefore both untestable in a model that treats dyads as
independent.

**Embeddedness** (Granovetter 1985; Uzzi 1996; Gulati 1995): new ties run
where old ties already run, because a prior relation carries information and
trust. In an affiliation network that means a director joins a board on which
he already has a board-mate from somewhere else. Adding the edge closes a
**four-cycle** — i sits on g, j sits on g and on f, so i-g-j-f-i — and the
count of four-cycles the edge would close is the embeddedness statistic. The
prediction is that the coefficient is positive.

**Structural holes** (Burt 1992): the return is to *bridging* disconnected
groups, so redundant contacts are waste. The prediction most often attributed
to Burt is that the coefficient is negative — ties should reach across the
holes rather than fill them in.

That reading is too quick, and the test here is built in two halves because of
it. Burt's claim is about **returns**, not about formation: brokers do better,
whoever forms the ties. So closure can govern who joins which board while
brokerage still governs who gains from the boards he is on, and the two halves
can come out differently without either theory being wrong. The halves are:

1. :func:`closure_design` and :func:`fit_closure` — does a prior board-mate on
   the board predict joining it? This is the formation half.
2. :func:`brokerage_panel` and :func:`returns_to_brokerage` — do directors in
   brokerage positions gain seats and survive into the next volume more than
   directors of the same seat count who are not? This is Burt's half.

**Everything on the right-hand side of the formation half is measured at
t-1.** The main fit in :mod:`politi.tergm` follows btergm and computes degree
change statistics on the observed network at t; here the whole specification
is lagged, because a shared board-mate measured at t could have arrived on the
same board in the same volume as the tie being explained. The cost is that the
coefficients are not numerically comparable with the main fit; the gain is
that nothing in the design is contemporaneous with the outcome.

**The seat-count trap applies, as it does everywhere in this dataset, and on
this question it has a specific shape.** The closure count is
``|mates(i) & board(f)|`` — the size of an intersection — so under random
matching its expectation is ``|mates(i)| * |board(f)| / N``. Both factors must
therefore be held fixed, and it is not enough to control the director's *seat*
count: a man with three seats on large boards has many board-mates and a high
closure count against every firm in the network. ``prior_mates`` is in the
model for that reason, alongside ``prior_board``, and `closure_expected` gives
the random-matching benchmark directly. :func:`closure_stratified` repeats the
comparison inside wave x mates x board-size cells with a within-cell
permutation null, which holds the arithmetic exactly fixed rather than
linearly.

The same trap, unhandled, is what makes the brokerage half of this module come
out one way before the contact-volume control and another way after it. See
`docs/EMBEDDEDNESS.md`.

**One projection is used, and only as a measure.** Burt's constraint and
effective size are defined on the ego network, so the brokerage half is
computed on the co-membership projection. That is legitimate for a *covariate*
and is not the thing this repository refuses: fitting an ERGM to a projection
is illegitimate because the projection manufactures a clique per board and the
model would then estimate that arithmetic as dependence. Measuring how
redundant a man's contacts are has no such problem — though the measure does
inherit the same clique structure, which is why the stratified comparison is
reported alongside it.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

#: Terms in the formation model. Everything is lagged to t-1.
CLOSURE_TERMS = ["edges", "prior_seats", "prior_mates", "prior_board", "closure",
                 "office", "origin_match",
                 "sector_finance", "sector_land_property", "sector_agriculture"]

#: Brokerage measures, and the direction each one points.
#: `open_share` and `effective_size` rise with brokerage; `constraint` falls.
BROKERAGE = ("open_share", "effective_size", "constraint")


# --- the formation half -------------------------------------------------------

def _wave_state(panel: dict, year: int) -> dict:
    """Adjacency in both directions for one wave."""
    edges = panel["edges"][year]
    seats: dict[str, set[str]] = {}
    board: dict[str, set[str]] = {}
    for person, firm in edges.to_numpy():
        seats.setdefault(person, set()).add(firm)
        board.setdefault(firm, set()).add(person)
    return {"seats": seats, "board": board}


def _mates(state: dict, person: str) -> dict[str, int]:
    """Prior board-mates of *person*, weighted by boards shared with him."""
    out: dict[str, int] = {}
    for firm in state["seats"].get(person, ()):
        for other in state["board"][firm]:
            if other != person:
                out[other] = out.get(other, 0) + 1
    return out


def _distance_to_firms(state: dict, person: str, firms: list[str]) -> dict[str, int]:
    """Geodesic distance from *person* to each firm in the two-mode graph.

    Unreachable firms get -1. Distance is odd by construction: 1 is a seat he
    holds, 3 is a board carrying one of his board-mates, 5 is two steps out.
    """
    seats, board = state["seats"], state["board"]
    seen_p = {person}
    seen_f: dict[str, int] = {}
    frontier = [person]
    step = 0
    while frontier:
        step += 1
        next_f = [f for p in frontier for f in seats.get(p, ()) if f not in seen_f]
        if not next_f:
            break
        for f in next_f:
            seen_f[f] = step
        step += 1
        frontier = [p for f in next_f for p in board.get(f, ()) if p not in seen_p]
        seen_p.update(frontier)
    return {f: seen_f.get(f, -1) for f in firms}


def closure_design(panel: dict) -> pd.DataFrame:
    """One row per at-risk dyad per transition, with the closure statistics.

    Columns beyond :data:`CLOSURE_TERMS`:

    ``memory``     the tie existed at t-1 — 0 selects the formation dyads.
    ``closure4``   four-cycles closed, counted with multiplicity: a board-mate
                   shared across two firms counts twice.
    ``distance``   geodesic distance from the director to the firm at t-1.
                   3 means a board-mate sits on it, so ``closure`` > 0 exactly
                   when ``distance`` is 3.
    ``prior_seats``   seats held at t-1.
    ``prior_mates``   distinct board-mates at t-1, anywhere in the network.
                   This, not seat count, is the factor the closure count is
                   mechanically driven by on the director's side.
    ``prior_board``   directors on the firm at t-1, the other factor.
    ``closure_expected``  ``prior_mates * prior_board / N`` — what the closure
                   count would be if board-mates were scattered at random over
                   the firms. The behavioural question is whether `closure`
                   predicts formation net of this.
    """
    n_persons = {}
    waves = panel["waves"]
    rows = []
    for previous, current in zip(waves, waves[1:]):
        persons = panel["persons"][current]
        firms = panel["firms"][current]
        before = _wave_state(panel, previous)
        prev_p = set(panel["persons"][previous].person_id)
        prev_f = set(panel["firms"][previous].company_id)

        at_risk_p = persons[persons.person_id.isin(prev_p)]
        at_risk_f = firms[firms.company_id.isin(prev_f)]
        if at_risk_p.empty or at_risk_f.empty:
            continue
        n_persons[current] = max(len(prev_p), 1)
        f_ids = list(at_risk_f.company_id)
        sectors = dict(zip(at_risk_f.company_id, at_risk_f.sector))
        # Board composition at t-1, restricted to the at-risk firm set.
        board_prior = {f: before["board"].get(f, set()) for f in f_ids}
        origin_prior = {}
        p_origin = dict(zip(persons.person_id, persons.origin))
        for f in f_ids:
            counts: dict[str, int] = {}
            for member in board_prior[f]:
                who = p_origin.get(member, "unknown")
                if who != "unknown":
                    counts[who] = counts.get(who, 0) + 1
            origin_prior[f] = counts

        now = set(map(tuple, panel["edges"][current].to_numpy()))

        for person, ego, has_office in zip(at_risk_p.person_id,
                                           at_risk_p.origin,
                                           at_risk_p.political):
            mates = _mates(before, person)
            held = before["seats"].get(person, set())
            dist = _distance_to_firms(before, person, f_ids)
            for firm in f_ids:
                members = board_prior[firm]
                # Four-cycles the edge would close. A board-mate met on f
                # itself is not a second path, so that share is removed --
                # which matters only for dyads already tied at t-1.
                paths = 0
                distinct = 0
                for mate in members:
                    weight = mates.get(mate, 0) - (1 if firm in held else 0)
                    if weight > 0:
                        paths += weight
                        distinct += 1
                same = origin_prior[firm].get(ego, 0) if ego != "unknown" else 0
                if firm in held:
                    same -= 1 if ego != "unknown" else 0
                rows.append((
                    current, person, firm,
                    int((person, firm) in now),
                    int(firm in held),
                    1,
                    len(held),
                    len(mates),
                    len(members) - (1 if firm in held else 0),
                    distinct,
                    paths,
                    dist[firm],
                    int(bool(has_office)),
                    max(same, 0),
                    int(sectors.get(firm) == "finance"),
                    int(sectors.get(firm) == "land_property"),
                    int(sectors.get(firm) == "agriculture"),
                ))
    out = pd.DataFrame(rows, columns=[
        "year", "person_id", "company_id", "tie", "memory",
        "edges", "prior_seats", "prior_mates", "prior_board", "closure", "closure4",
        "distance", "office", "origin_match",
        "sector_finance", "sector_land_property", "sector_agriculture"])
    out["closure_any"] = (out.closure > 0).astype(int)
    out["closure_log"] = np.log1p(out.closure)
    out["closure_expected"] = (out.prior_mates * out.prior_board
                               / out.year.map(n_persons))
    out["closure_excess"] = out.closure - out.closure_expected
    return out


def fit_closure(design: pd.DataFrame, closure: str = "closure",
                n_boot: int = 200, seed: int = 20260913) -> pd.DataFrame:
    """Fit the formation half: the closure term against both degrees.

    Fitted on `memory == 0` — the dyads not tied at t-1, which are the only
    ones on which "does a tie form?" is a question. *closure* selects the
    functional form: the count, `closure_any` for the binary, `closure_log`
    for a concave one, `closure4` for four-cycles with multiplicity.
    """
    from .tergm import fit_mple

    terms = [closure if t == "closure" else t for t in CLOSURE_TERMS]
    fitted = fit_mple(design[design.memory == 0], terms=terms,
                      n_boot=n_boot, seed=seed)
    fitted.insert(0, "form", closure)
    return fitted


def fit_baseline(design: pd.DataFrame, n_boot: int = 200,
                 seed: int = 20260913) -> pd.DataFrame:
    """The same lagged specification with no closure term at all.

    Fitted so the closure result can be read as a contribution rather than
    asserted. If closure were standing in for community homophily -- men join
    boards where their board-mates are, and their board-mates are of their own
    community -- then `origin_match` would fall when closure enters. It moves
    from +0.311 to +0.297, which is to say it does not: the two are separate
    and additive channels, not one channel measured twice.
    """
    from .tergm import fit_mple

    terms = [t for t in CLOSURE_TERMS if t != "closure"]
    fitted = fit_mple(design[design.memory == 0], terms=terms,
                      n_boot=n_boot, seed=seed)
    fitted.insert(0, "form", "none")
    return fitted


def distance_table(design: pd.DataFrame) -> pd.DataFrame:
    """Formation rate by prior distance — the descriptive form of the test.

    Distance 3 is a board with a prior board-mate on it. If embeddedness holds,
    the rate at 3 is far above the rate at 5 and beyond; if ties bridge holes,
    it is not.
    """
    form = design[design.memory == 0].copy()
    band = form.distance.where(form.distance <= 5, 7)
    band = band.where(form.distance >= 0, -1)
    out = (form.assign(band=band).groupby("band")
           .agg(dyads=("tie", "size"), formed=("tie", "sum"),
                prior_seats=("prior_seats", "mean"),
                prior_board=("prior_board", "mean")).reset_index())
    out["rate_per_1000"] = out.formed / out.dyads * 1000
    labels = {-1: "unreachable", 3: "3 (a board-mate sits on it)",
              5: "5 (two steps out)", 7: "7 or more"}
    out["band"] = out.band.map(lambda b: labels.get(int(b), str(b)))
    return out


def closure_stratified(design: pd.DataFrame, n_perm: int = 2000,
                       seed: int = 7, min_cell: int = 30) -> dict:
    """Is closure above chance once both degrees are held exactly fixed?

    Compares the mean closure count of dyads that formed against dyads that
    did not, inside wave x board-mates x board-size cells, with a null that
    permutes *which dyads formed* inside each cell. Both factors of the
    expected closure count are constant within a cell up to the binning, so
    the arithmetic that produces the raw difference cannot produce the
    within-cell one.
    """
    rng = np.random.default_rng(seed)
    frame = design[design.memory == 0].reset_index(drop=True)
    board_bin = np.minimum(frame.prior_board.to_numpy(), 12)
    mate_bin = pd.cut(frame.prior_mates, [-1, 0, 3, 6, 10, 20, 10_000],
                      labels=False).to_numpy()
    tie = frame.tie.to_numpy().astype(bool)
    values = frame.closure.to_numpy(dtype=float)
    keys = pd.DataFrame({"year": frame.year, "mates": mate_bin,
                         "board": board_bin})
    cells = [np.asarray(i) for i in keys.groupby(list(keys.columns)).indices.values()]
    usable = [c for c in cells
              if tie[c].sum() >= 3 and (~tie[c]).sum() >= min_cell]

    def pooled(mark: np.ndarray) -> float:
        num = den = 0.0
        for c in usable:
            a, b = mark[c], ~mark[c]
            w = a.sum() * b.sum() / (a.sum() + b.sum())
            num += (values[c][a].mean() - values[c][b].mean()) * w
            den += w
        return num / den if den else float("nan")

    observed = pooled(tie)
    draws = np.empty(n_perm)
    for i in range(n_perm):
        shuffled = tie.copy()
        for c in usable:
            v = shuffled[c].copy()
            rng.shuffle(v)
            shuffled[c] = v
        draws[i] = pooled(shuffled)
    return {"raw": float(values[tie].mean() - values[~tie].mean()),
            "within_cells": float(observed),
            "p_perm": float(np.mean(np.abs(draws) >= abs(observed))),
            "null_lo": float(np.percentile(draws, 2.5)),
            "null_hi": float(np.percentile(draws, 97.5)),
            "cells": len(usable), "formed": int(tie.sum())}


# --- Burt's half: returns to brokerage ---------------------------------------

def brokerage_panel(panel: dict) -> pd.DataFrame:
    """Per director per wave: brokerage at t, and what happened by t+1.

    Brokerage is measured three ways on the co-membership projection of the
    wave: `open_share` (the share of his board-mate pairs who share no board
    with each other), `effective_size` and Burt's `constraint`. The first two
    rise with brokerage, the third falls.

    Outcomes are `survives` (he appears in the next volume at all), `new_seats`
    (seats at t+1 he did not hold at t) and `growth`. The last wave has no
    successor and is dropped.
    """
    import networkx as nx

    from .network import _project

    waves = panel["waves"]
    rows = []
    for index, year in enumerate(waves[:-1]):
        nxt = waves[index + 1]
        state = _wave_state(panel, year)
        state_next = _wave_state(panel, nxt)
        alive_next = set(panel["persons"][nxt].person_id)

        g = nx.Graph()
        for person, firm in panel["edges"][year].to_numpy():
            g.add_node(person, kind="person")
            g.add_node(firm, kind="company")
            g.add_edge(person, firm)
        proj = _project(g, [n for n, d in g.nodes(data=True)
                            if d["kind"] == "person"], "person")
        constraint = nx.constraint(proj, weight="weight")
        effective = nx.effective_size(proj, weight="weight")

        persons = panel["persons"][year]
        for person, origin, office in zip(persons.person_id, persons.origin,
                                          persons.political):
            mates = set(_mates(state, person))
            pairs = list(combinations(sorted(mates), 2))
            open_pairs = sum(1 for a, b in pairs
                             if not (state["seats"].get(a, set())
                                     & state["seats"].get(b, set())))
            held = state["seats"].get(person, set())
            later = state_next["seats"].get(person, set())
            rows.append({
                "year": year, "next_year": nxt, "person_id": person,
                "origin": origin, "office": bool(office),
                "seats": len(held), "mates": len(mates), "pairs": len(pairs),
                "open_share": open_pairs / len(pairs) if pairs else np.nan,
                "effective_size": effective.get(person, np.nan),
                "constraint": constraint.get(person, np.nan),
                "survives": person in alive_next,
                "seats_next": len(later),
                "new_seats": len(later - held),
            })
    out = pd.DataFrame(rows)
    out["growth"] = out.seats_next - out.seats
    out["seat_cat"] = out.seats.clip(upper=5)
    return out


def returns_to_brokerage(broker: pd.DataFrame, outcome: str = "new_seats",
                         n_perm: int = 3000, seed: int = 11,
                         min_cell: int = 8) -> pd.DataFrame:
    """Do brokers do better, compared only with directors of the same size?

    For each measure in :data:`BROKERAGE`, directors are split at the median of
    that measure inside their wave x seat-count cell and the outcome compared
    within the cell, with a within-cell permutation null. Directors holding one
    seat are dropped: a single board makes every board-mate pair connected
    through that board, so `open_share` is 0 for all of them by construction
    and there is nothing to split.
    """
    from .sectors import stratified_gap

    frame = broker[broker.seats >= 2].dropna(subset=["open_share"]).copy()
    out = []
    for measure in BROKERAGE:
        work = frame.dropna(subset=[measure]).copy()
        median = work.groupby(["year", "seat_cat"])[measure].transform("median")
        work["broker"] = work[measure] > median
        if measure == "constraint":       # constraint falls with brokerage
            work["broker"] = work[measure] < median
        result = stratified_gap(work, outcome, term="broker",
                                n_perm=n_perm, seed=seed, min_cell=min_cell)
        result["brokerage"] = measure
        result["outcome"] = outcome
        out.append(result)
    return pd.DataFrame(out)[["brokerage", "outcome", "raw", "within_cells",
                              "p_perm", "null_lo", "null_hi", "cells", "n"]]


def brokerage_regression(broker: pd.DataFrame, outcome: str = "new_seats"
                         ) -> pd.DataFrame:
    """Burt's claim against the volume of contacts, in one model.

    The stratified comparison in :func:`returns_to_brokerage` holds the seat
    count fixed, and on `new_seats` it reports a brokerage advantage. That
    advantage does not survive the control that matters. Burt's distinctive
    claim is not that more contacts help — Coleman's closure account predicts
    that too — but that **non-redundant** contacts help *at a given number of
    contacts*. So the number of board-mates has to be in the model, and when it
    is, the brokerage measures go flat and the board-mate count carries the
    association.

    Poisson with cluster-robust standard errors by director, wave fixed
    effects, seat count as a factor. Multi-seat directors only.
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    frame = broker[broker.seats >= 2].dropna(subset=list(BROKERAGE)).copy()
    frame["wave"] = frame.year.astype("category")
    frame["seat_f"] = frame.seat_cat.astype("category")
    rows = []
    for measure in BROKERAGE:
        for label, formula in (
                ("seats only", f"{outcome} ~ wave + seat_f + {measure}"),
                ("seats + contact volume",
                 f"{outcome} ~ wave + seat_f + mates + {measure}")):
            fit = smf.glm(formula, data=frame,
                          family=sm.families.Poisson()).fit(
                cov_type="cluster", cov_kwds={"groups": frame.person_id})
            ci = fit.conf_int()
            for term in ([measure] if label == "seats only"
                         else ["mates", measure]):
                rows.append({"model": label, "brokerage": measure,
                             "outcome": outcome, "term": term,
                             "coef": fit.params[term],
                             "lo": ci.loc[term, 0], "hi": ci.loc[term, 1],
                             "p": fit.pvalues[term], "n": int(fit.nobs)})
    return pd.DataFrame(rows)
