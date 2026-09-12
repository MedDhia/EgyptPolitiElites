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
