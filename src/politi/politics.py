"""Political office held by directors, read from the roster entries.

Politi's roster does not only list board seats. Alongside them it prints the
public offices a director held or had held::

    S.E. Sadek, Wahba (Pacha), Sénateur; ancien Ministre; Vice-Président …
    S.E. Abdel Rahman el Bialy Bey, Ancien Ministre des Finances, Président …
    … Ministre des Wakfs, député de Bassioun, Ex-Gouverneur du …

Those lines are the source of the political-connection variables. This module
reads them out of the entry as printed and codes them into seven offices.

Three properties of the coding are worth stating plainly, because they bound
every use of it:

* **It is a floor, not a census.** Politi printed an office when he had it.
  A director with no office coded here may simply not have had one recorded.
  Read every rate below as "at least this many", and read change across waves
  as change in what the annuaire printed as much as in who sat on boards.
* **Most offices are past.** The overwhelming majority are printed as *ancien*
  or *ex-*. `former` records that. A former minister is a political connection
  — arguably a better one than a sitting minister, since he is free to sit on
  boards — but he is not a serving official, and the two must not be conflated.
* **"Ministre" is two different jobs.** *Ministre des Finances* is a cabinet
  post; *Ministre Plénipotentiaire* and *Ministre d'Égypte à Paris* are
  diplomatic ranks. They are separated here; conflating them would roughly
  double the apparent size of the cabinet-connected group.

Offices are read from the name and the body the parser produced, not from the
whole entry as scanned. Where the entry splitter has merged two directors — it
does so rarely, and `origin.is_person` catches most of the wreckage — an office
can still be attributed to the neighbour above it.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from unidecode import unidecode

from .biographies import Biography

# --- office vocabulary --------------------------------------------------------
#
# Each pattern is matched against the entry with accents folded and case
# ignored. `EXCLUSIONS` is applied first, so a phrase that carries an office's
# word without the office cannot code it.

#: Matches that carry an office's word but not the office. A match starting at
#: one of these positions is discarded before the office is coded.
EXCLUSIONS: dict[str, re.Pattern[str]] = {
    # A *ministre* who is a diplomat rather than a member of the cabinet.
    "cabinet": re.compile(
        r"(?i)ministre\s+(?:plenipotentiaire|d[e']\s*egypte\b|"
        r"de\s+sa\s+majeste|a\s+[A-Z])"),
    # The governor of the National Bank is a banker, and a Rotary district
    # governor is not in government at all.
    "provincial": re.compile(
        r"(?i)(?:sous[\s-])?gouverneur\s+(?:de\s+la\s+|du\s+|d[e']\s*)?"
        r"(?:\S+\s+){0,3}?(?:banque|bank|rotary|club|societe|company|cie\b)"),
}

OFFICES: dict[str, re.Pattern[str]] = {
    # Cabinet: a portfolio, the premiership, or an under-secretaryship of state.
    "cabinet": re.compile(
        r"(?i)\bministre\b|\bministere\b|"
        r"sous[\s-]secretaire\s+d[e']\s*etat|"
        r"president\s+du\s+conseil\s+des\s+ministres"),
    # Parliament: the Chamber of Deputies or the Senate.
    "parliament": re.compile(
        r"(?i)\bdeputes?\b|\bsenateur\b|chambre\s+des\s+deputes|\bsenat\b|"
        r"\bparlement\b"),
    # Diplomatic service.
    "diplomatic": re.compile(
        r"(?i)\bambassadeur\b|\bconsul\s+general\b|\bconsul\s+d[e']|"
        r"envoye\s+extraordinaire|ministre\s+plenipotentiaire|"
        r"ministre\s+d[e']\s*egypte\b|\blegation\b"),
    # Provincial administration: a governorate or a province.
    "provincial": re.compile(
        r"(?i)\bgouverneur\b|\bmoudir\b|\bmoudirieh\b|\bmouhafez\b|"
        r"\bmohafez\b|\bgouvernorat\b"),
    # Bench and state legal service.
    "judicial": re.compile(
        r"(?i)\bmagistrat\b|\bjuge\b|conseiller\s+d[e']\s*etat|"
        r"conseil\s+d[e']\s*etat|\bprocureur\b|cour\s+d[e']\s*appel|"
        r"tribunaux?\s+mixtes?|parquet\b"),
    # The royal household.
    "court": re.compile(
        r"(?i)\bchambellan\b|cabinet\s+royal|maison\s+royale|"
        r"grand\s+maitre\s+de\s+la\s+cour|aide\s+de\s+camp\s+du\s+roi"),
    # Municipal government.
    "municipal": re.compile(
        r"(?i)conseil(?:ler)?\s+municipal|commission\s+municipale|"
        r"municipalite\s+d"),
}

#: Marks an office as held in the past rather than at the time of printing.
_FORMER = re.compile(r"(?i)\b(?:anc(?:ien(?:ne)?s?|\.)|ex)[\s-]*$")

#: How much text before an office mention is read for an "ancien" qualifier.
_FORMER_WINDOW = 24

#: Offices treated as national political office when a single flag is wanted.
NATIONAL = ("cabinet", "parliament", "diplomatic", "provincial", "court")

OFFICE_LABEL = {
    "cabinet": "Cabinet",
    "parliament": "Parliament",
    "diplomatic": "Diplomatic service",
    "provincial": "Provincial administration",
    "judicial": "Bench and state legal service",
    "court": "Royal household",
    "municipal": "Municipal government",
}


def _fold(text: str) -> str:
    """Accent-folded, whitespace-normalised text for matching."""
    return re.sub(r"\s+", " ", unidecode(str(text)))


def find_offices(entry: str) -> dict[str, bool]:
    """Return the offices named in one roster entry, mapped to *former*.

    ``True`` means every mention of that office is qualified as past
    ("ancien Ministre", "ex-Gouverneur"); ``False`` means at least one is
    printed as current.
    """
    text = _fold(entry)
    found: dict[str, bool] = {}
    for office, pattern in OFFICES.items():
        matches = list(pattern.finditer(text))
        veto = EXCLUSIONS.get(office)
        if veto is not None:
            # Drop matches that open a phrase carrying the word but not the
            # office, and keep the office only if something remains.
            spans = [(m.start(), m.end()) for m in veto.finditer(text)]
            matches = [m for m in matches
                       if not any(a <= m.start() < b for a, b in spans)]
        if not matches:
            continue
        found[office] = all(
            bool(_FORMER.search(text[max(0, m.start() - _FORMER_WINDOW):m.start()]))
            for m in matches)
    return found


def office_frame(rosters: dict[int, list[Biography]]) -> pd.DataFrame:
    """One row per (wave, printed entry, office) across every parsed roster.

    Keyed on the printed name, since this runs before record linkage; join it
    to the dataset with :func:`attach_offices`.
    """
    rows = []
    for year, bios in sorted(rosters.items()):
        for bio in bios:
            if not bio.name:
                continue
            # The crosswalk keys mentions on honorific-plus-name, so emit
            # exactly that string or the join in `attach_offices` finds nothing.
            printed_name = f"{bio.honorific + ' ' if bio.honorific else ''}{bio.name}"
            for office, former in find_offices(f"{bio.name}, {bio.body}").items():
                rows.append({"year": year, "printed_name": printed_name,
                             "office": office, "former": former,
                             "source_page": bio.page})
    return pd.DataFrame(rows, columns=["year", "printed_name", "office",
                                       "former", "source_page"])


def attach_offices(offices: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Resolve the office rows onto `person_id` using the person crosswalk.

    The crosswalk carries one row per mention, so it is deduplicated to one
    row per (wave, printed name) before joining; a director listed against six
    firms must not multiply his single ministry by six.
    """
    if offices.empty or crosswalk.empty:
        return pd.DataFrame(columns=["year", "person_id", "office", "former"])
    key = (crosswalk[["year", "printed_name", "person_id"]]
           .drop_duplicates(["year", "printed_name"]))
    out = offices.merge(key, on=["year", "printed_name"], how="inner")
    return (out[["year", "person_id", "office", "former", "source_page"]]
            .drop_duplicates(["year", "person_id", "office"])
            .sort_values(["year", "person_id", "office"], ignore_index=True))


def person_flags(offices: pd.DataFrame) -> pd.DataFrame:
    """Collapse the long office table to one row per person-wave.

    Columns: the seven office booleans, `n_offices`, `political` (any office),
    `national` (any office in :data:`NATIONAL`), and `all_former`.
    """
    cols = list(OFFICES)
    if offices.empty:
        return pd.DataFrame(columns=["year", "person_id", *cols, "n_offices",
                                     "political", "national", "all_former"])
    wide = (offices.assign(held=True)
            .pivot_table(index=["year", "person_id"], columns="office",
                         values="held", aggfunc="any", fill_value=False)
            .reindex(columns=cols, fill_value=False)
            .reset_index())
    former = (offices.groupby(["year", "person_id"]).former.all()
              .rename("all_former").reset_index())
    wide = wide.merge(former, on=["year", "person_id"], how="left")
    wide["n_offices"] = wide[cols].sum(axis=1)
    wide["political"] = wide["n_offices"] > 0
    wide["national"] = wide[list(NATIONAL)].any(axis=1)
    return wide


def firm_flags(aff: pd.DataFrame, flags: pd.DataFrame) -> pd.DataFrame:
    """Political connection at the level of the firm-wave.

    `n_political` counts the firm's recorded directors holding any office and
    `share_political` divides it by the directors recorded for that firm — a
    share of the roster's coverage of the board, not of the board (see
    `docs/FIGURES_EXPLORE.md`).
    """
    if aff.empty:
        return pd.DataFrame(columns=["year", "company_id", "n_directors",
                                     "n_political", "share_political",
                                     "connected"])
    d = aff.drop_duplicates(["year", "company_id", "person_id"])
    if flags.empty:
        d = d.assign(political=False, national=False)
    else:
        d = d.merge(flags[["year", "person_id", "political", "national"]],
                    on=["year", "person_id"], how="left")
        d[["political", "national"]] = d[["political", "national"]].fillna(False)
    # Cast before aggregating: summing an object-dtype boolean column returns
    # `False` rather than 0 for a one-director firm, and the column then reads
    # back from CSV as a string.
    d[["political", "national"]] = d[["political", "national"]].astype(bool).astype(int)
    g = (d.groupby(["year", "company_id"])
          .agg(n_directors=("person_id", "nunique"),
               n_political=("political", "sum"),
               n_national=("national", "sum")).reset_index())
    g["share_political"] = g.n_political / g.n_directors
    g["connected"] = g.n_political > 0
    return g


# --- analysis -----------------------------------------------------------------

def political_panel(processed=None) -> pd.DataFrame:
    """The positional panel with the political-office flags merged in.

    Directors with no row in `person_political.csv` held no office Politi
    printed, which is coded ``False`` rather than missing — see the floor
    caveat at the top of this module.
    """
    from pathlib import Path

    from . import config
    from .positional import build_panel

    processed = Path(processed) if processed else config.PROCESSED
    panel = build_panel(processed)
    path = processed / "person_political.csv"
    cols = [*OFFICES, "political", "national", "n_offices", "all_former"]
    if not path.exists():
        for c in cols:
            panel[c] = False if c != "n_offices" else 0
        return panel
    flags = pd.read_csv(path)
    panel = panel.merge(flags[["year", "person_id", *cols]],
                        on=["year", "person_id"], how="left")
    for c in [*OFFICES, "political", "national", "all_former"]:
        panel[c] = panel[c].fillna(False).astype(bool)
    panel["n_offices"] = panel.n_offices.fillna(0).astype(int)
    return panel


def office_by_wave(panel: pd.DataFrame, outcome: str = "bcp_log",
                   degree_control: str = "deg_proj_z",
                   term: str = "political") -> pd.DataFrame:
    """The political-office coefficient wave by wave, net of connectedness.

    Same specification as `positional.by_wave`: OLS on the log of projected
    betweenness with a standardised projection-degree control and HC1 errors.

    Associational, and in neither direction: office and directorship are
    printed in the same entry, so the two are simultaneous here. See the
    Wording section of `docs/POLITICAL_CONNECTIONS.md`.
    """
    import warnings

    import statsmodels.formula.api as smf

    rows = []
    for year, chunk in panel.groupby("year"):
        if chunk[term].nunique() < 2:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.ols(f"{outcome} ~ {term} + {degree_control}",
                        data=chunk.assign(**{term: chunk[term].astype(int)})
                        ).fit(cov_type="HC1")
        ci = m.conf_int().loc[term]
        rows.append({"year": int(year), "coef": m.params[term],
                     "se": m.bse[term], "lo": ci[0], "hi": ci[1],
                     "p": m.pvalues[term], "n": int(chunk.shape[0]),
                     "n_office": int(chunk[term].sum())})
    return pd.DataFrame(rows)


def origin_with_political(panel: pd.DataFrame, outcome: str = "bcp_log",
                          degree_control: str = "deg_proj_z") -> pd.DataFrame:
    """Origin coefficients with and without the political-office control.

    If office holding is the channel through which Arab/Egyptian directors
    reach brokerage positions, adding it should move the origin coefficients
    away from zero — the European coefficient should *rise*, because the
    comparison is then between directors with the same political standing.
    """
    import warnings

    import statsmodels.formula.api as smf

    from .positional import REFERENCE

    df = panel[panel.origin != "unknown"].copy()
    df["origin"] = df.origin.cat.remove_unused_categories()
    df["political"] = df.political.astype(int)
    base = f'C(origin, Treatment("{REFERENCE}"))'
    rows = []
    for year, chunk in df.groupby("year"):
        for label, formula in (
                ("without", f"{outcome} ~ {base} + {degree_control}"),
                ("with", f"{outcome} ~ {base} + political + {degree_control}")):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = smf.ols(formula, data=chunk).fit(cov_type="HC1")
            for grp in ("european", "local_minority"):
                t = f"{base}[T.{grp}]"
                if t not in m.params.index:
                    continue
                ci = m.conf_int().loc[t]
                rows.append({"year": int(year), "group": grp, "spec": label,
                             "coef": m.params[t], "se": m.bse[t],
                             "lo": ci[0], "hi": ci[1], "p": m.pvalues[t],
                             "n": int(chunk.shape[0])})
    return pd.DataFrame(rows)


# --- persistence --------------------------------------------------------------

def persistence_panel(processed=None) -> pd.DataFrame:
    """Firm-wave observations with whether the firm appears in the next wave.

    **The outcome is presence in the next volume, not survival of the firm.**
    A firm is recorded in a wave only if at least one of its directors is
    listed in that volume's roster, so a firm can vanish from the register
    while trading on. Every quantity built from this is about the annuaire's
    coverage as much as about the company.

    The last wave has no successor and is dropped. `gap_years` records the
    interval to the next wave, which is 6, 4, 5 and 3 years — a firm has more
    time to disappear between 1932 and 1938 than between 1947 and 1950.
    """
    from pathlib import Path

    from . import config
    from .origin import is_person

    processed = Path(processed) if processed else config.PROCESSED
    aff = pd.read_csv(processed / "affiliations.csv")
    aff = aff[aff.person_label.map(is_person)]
    firm = pd.read_csv(processed / "firm_political.csv")

    waves = sorted(aff.year.unique())
    following = dict(zip(waves, waves[1:]))
    present = set(zip(aff.year, aff.company_id))

    # How many boards the firm's best-connected director sits on, this wave.
    # A firm tied to a man with eight seats is likelier to be listed again
    # whatever its politics, so this is the second artefact control.
    seats = (aff.groupby(["year", "person_id"]).company_id.nunique()
             .rename("seats").reset_index())
    anchor = (aff.merge(seats, on=["year", "person_id"])
              .groupby(["year", "company_id"]).seats.max()
              .rename("max_seats").reset_index())

    d = (firm[firm.year != waves[-1]]
         .merge(anchor, on=["year", "company_id"], how="left"))
    d["max_seats"] = d.max_seats.fillna(1)
    d["reappears"] = [int((following[y], c) in present)
                      for y, c in zip(d.year, d.company_id)]
    d["gap_years"] = d.year.map(
        {a: b - a for a, b in zip(waves, waves[1:])})
    d["log_directors"] = np.log(d.n_directors)
    d["log_max_seats"] = np.log(d.max_seats)
    #: Capped so the top category is not a single firm.
    d["directors_cat"] = d.n_directors.clip(upper=5)
    return d


#: Specifications reported by :func:`persistence_models`, in order.
PERSISTENCE_SPECS = [
    ("raw", "reappears ~ conn", "No controls"),
    ("wave", "reappears ~ conn + C(year)", "Wave"),
    ("directors", "reappears ~ conn + C(year) + C(directors_cat)",
     "Wave, directors recorded"),
    ("anchor", "reappears ~ conn + C(year) + C(directors_cat) + log_max_seats",
     "Wave, directors recorded, their seat counts"),
]


def persistence_models(panel: pd.DataFrame, term: str = "connected") -> pd.DataFrame:
    """Logistic models of reappearance, adding one artefact control at a time.

    Reported as odds ratios with firm-clustered errors. These are associations
    between how a firm is *recorded* and whether it is recorded again; they do
    not identify an effect of political connection on anything, and the
    direction of any association is not established by them.
    """
    import warnings

    import statsmodels.formula.api as smf

    d = panel.assign(conn=panel[term].astype(bool).astype(int))
    rows = []
    for key, formula, label in PERSISTENCE_SPECS:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.logit(formula, data=d).fit(
                disp=0, cov_type="cluster", cov_kwds={"groups": d.company_id})
        ci = m.conf_int().loc["conn"]
        rows.append({"spec": key, "controls": label,
                     "coef": m.params["conn"], "or": np.exp(m.params["conn"]),
                     "lo": np.exp(ci[0]), "hi": np.exp(ci[1]),
                     "p": m.pvalues["conn"], "n": int(m.nobs)})
    return pd.DataFrame(rows)


def persistence_stratified(panel: pd.DataFrame, term: str = "connected",
                           n_perm: int = 4000, seed: int = 11,
                           min_cell: int = 5) -> dict:
    """Exact comparison inside wave × recorded-directors cells.

    The regression above imposes a functional form; this does not. Firms are
    compared only with firms in the same wave recorded through the same number
    of directors, and the cell differences are pooled with inverse-variance
    weights. The null permutes the connection flag *within* each cell, so it
    holds the composition that drives the raw gap exactly fixed.

    Returns the cell table, the pooled difference in percentage points, the
    two-sided permutation p, and the null interval.
    """
    rng = np.random.default_rng(seed)
    flag = panel[term].astype(bool).to_numpy()
    outcome = panel.reappears.to_numpy()
    cells = [np.asarray(idx) for idx in
             panel.reset_index(drop=True).groupby(["year", "directors_cat"])
             .indices.values()]
    usable = [c for c in cells
              if flag[c].sum() >= min_cell and (~flag[c]).sum() >= min_cell]

    def pooled(marks: np.ndarray) -> float:
        num = den = 0.0
        for c in usable:
            a, b = marks[c], ~marks[c]
            w = a.sum() * b.sum() / (a.sum() + b.sum())
            num += (outcome[c][a].mean() - outcome[c][b].mean()) * w
            den += w
        return num / den if den else float("nan")

    observed = pooled(flag)
    draws = np.empty(n_perm)
    for i in range(n_perm):
        shuffled = flag.copy()
        for c in usable:
            v = shuffled[c].copy()
            rng.shuffle(v)
            shuffled[c] = v
        draws[i] = pooled(shuffled)

    table = pd.DataFrame([{
        "year": int(panel.year.to_numpy()[c][0]),
        "directors": int(panel.directors_cat.to_numpy()[c][0]),
        "connected": outcome[c][flag[c]].mean(),
        "unconnected": outcome[c][~flag[c]].mean(),
        "difference": outcome[c][flag[c]].mean() - outcome[c][~flag[c]].mean(),
        "n_connected": int(flag[c].sum()),
        "n_unconnected": int((~flag[c]).sum()),
    } for c in usable]).sort_values(["year", "directors"], ignore_index=True)

    return {"cells": table, "pooled_pts": observed * 100,
            "p_perm": float(np.mean(np.abs(draws) >= abs(observed))),
            "null_lo_pts": float(np.percentile(draws, 2.5)) * 100,
            "null_hi_pts": float(np.percentile(draws, 97.5)) * 100,
            "n_cells": len(usable)}
