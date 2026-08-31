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


# --- survival -----------------------------------------------------------------

#: Reasons the survival analysis is discrete-time rather than Cox.
SURVIVAL_DESIGN = """\
Firms are observed at five unequally spaced points, not continuously, so the
data are interval-censored and a Cox model would misstate what is known. This
is a discrete-time hazard model on the firm-wave risk set, with a
complementary log-log link and log(interval) as an offset — the specification
whose coefficients are proportional hazards on the underlying continuous time,
and whose offset makes the 6-, 4-, 5- and 3-year intervals comparable.

Four features of the data bound what it can say:

* **The event is leaving the register, not failing.** A firm drops out of the
  risk set when the next volume does not record it. It may have been wound up,
  or merely gone unlisted. Nothing here distinguishes the two.
* **Entry is left-truncated.** Firms were trading before 1932 and the volumes
  do not give a founding date, so the clock runs from first appearance in the
  register, not from incorporation. `tenure` is volumes observed, never age.
* **Disappearance is not absorbing.** 5.4% of firms reappear after a missing
  wave, which the primary specification treats as an exit. `permanent_exit`
  builds the alternative, where the spell ends at the last wave the firm is
  recorded in.
* **Wave, tenure and entry cohort are collinear.** Given the wave and the
  tenure, the entry cohort is determined. Wave and tenure are in the model and
  the cohort is therefore absorbed, not estimated.
"""


def survival_panel(processed=None, permanent_exit: bool = False) -> pd.DataFrame:
    """The firm-wave risk set for the discrete-time hazard model.

    One row per wave a firm is recorded in and at risk of not being recorded
    in the next. `exit` is the event; `gap` is the interval to the next wave,
    which belongs in the model as an offset. Firms recorded in the last wave
    are right-censored and contribute no row for it.

    Set *permanent_exit* to end the spell at the firm's last recorded wave
    rather than at its first missing one. See :data:`SURVIVAL_DESIGN`.
    """
    from pathlib import Path

    from . import config
    from .origin import is_person

    processed = Path(processed) if processed else config.PROCESSED
    aff = pd.read_csv(processed / "affiliations.csv")
    aff = aff[aff.person_label.map(is_person)]
    firm = pd.read_csv(processed / "firm_political.csv")

    waves = sorted(aff.year.unique())
    presence = {c: set(g) for c, g in aff.groupby("company_id").year}

    seats = (aff.groupby(["year", "person_id"]).company_id.nunique()
             .rename("seats").reset_index())
    anchor = (aff.merge(seats, on=["year", "person_id"])
              .groupby(["year", "company_id"]).seats.max()
              .rename("max_seats").reset_index())

    rows = []
    for company, years in presence.items():
        first, last = min(years), max(years)
        tenure = 0
        for i, wave in enumerate(waves):
            if wave < first:
                continue
            if permanent_exit:
                if wave > last:
                    break
                if wave not in years:
                    continue            # an internal gap is not an exit here
            elif wave not in years:
                break                   # the first missing wave ends the spell
            tenure += 1
            if i == len(waves) - 1:
                break                   # censored: no following volume
            event = int(wave == last) if permanent_exit \
                else int(waves[i + 1] not in years)
            rows.append({"company_id": company, "year": wave, "tenure": tenure,
                         "entry": first, "exit": event,
                         "gap": waves[i + 1] - wave})

    d = (pd.DataFrame(rows)
         .merge(firm, on=["year", "company_id"], how="left")
         .merge(anchor, on=["year", "company_id"], how="left"))
    d["max_seats"] = d.max_seats.fillna(1)
    d["log_gap"] = np.log(d.gap)
    d["log_max_seats"] = np.log(d.max_seats)
    d["tenure_cat"] = d.tenure.clip(upper=4)
    d["directors_cat"] = d.n_directors.clip(upper=5)
    return d


#: Specifications reported by :func:`survival_models`, in order.
SURVIVAL_SPECS = [
    ("baseline", "exit ~ conn + C(year) + C(tenure_cat)",
     "Wave, tenure"),
    ("directors",
     "exit ~ conn + C(year) + C(tenure_cat) + C(directors_cat)",
     "Wave, tenure, directors recorded"),
    ("anchor",
     "exit ~ conn + C(year) + C(tenure_cat) + C(directors_cat) + log_max_seats",
     "Wave, tenure, directors recorded, their seat counts"),
]


def survival_models(panel: pd.DataFrame, term: str = "connected") -> pd.DataFrame:
    """Discrete-time hazard ratios for leaving the register.

    Complementary log-log with a log-interval offset and firm-clustered
    errors, so `hr` is a hazard ratio. Below 1 is a lower hazard of dropping
    out of the annuaire, which is not the same as a lower risk of failing.

    Association only, and in no direction: connection and presence are read
    from the same volume.
    """
    import warnings

    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    d = panel.assign(conn=panel[term].astype(bool).astype(int))
    binomial = sm.families.Binomial(sm.families.links.CLogLog())
    rows = []
    for key, formula, label in SURVIVAL_SPECS:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.glm(formula, data=d, family=binomial, offset=d.log_gap).fit(
                cov_type="cluster", cov_kwds={"groups": d.company_id})
        ci = m.conf_int().loc["conn"]
        rows.append({"spec": key, "controls": label,
                     "coef": m.params["conn"], "hr": np.exp(m.params["conn"]),
                     "lo": np.exp(ci[0]), "hi": np.exp(ci[1]),
                     "p": m.pvalues["conn"], "n": int(m.nobs),
                     "events": int(d.exit.sum())})
    return pd.DataFrame(rows)


def survival_ph_test(panel: pd.DataFrame, term: str = "connected") -> pd.DataFrame:
    """Does the association vary with tenure or with the wave?

    A joint Wald test on the interaction block. A small p would mean the
    single hazard ratio above is an average over something that moves.
    """
    import warnings

    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    d = panel.assign(conn=panel[term].astype(bool).astype(int))
    binomial = sm.families.Binomial(sm.families.links.CLogLog())
    rows = []
    for label, formula in (
            ("tenure",
             "exit ~ conn*C(tenure_cat) + C(year) + C(directors_cat)"),
            ("wave",
             "exit ~ conn*C(year) + C(tenure_cat) + C(directors_cat)")):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = smf.glm(formula, data=d, family=binomial, offset=d.log_gap).fit(
                cov_type="cluster", cov_kwds={"groups": d.company_id})
            table = m.wald_test_terms().table
        key = next(i for i in table.index if i.startswith("conn:"))
        rows.append({"interaction": label,
                     "chi2": float(np.ravel(table.loc[key, "statistic"])[0]),
                     "df": int(table.loc[key, "df_constraint"]),
                     "p": float(np.ravel(table.loc[key, "pvalue"])[0])})
    return pd.DataFrame(rows)


def life_table(panel: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    """Discrete hazard and survivor function over tenure in the register.

    The survivor function is the running product of one minus the interval
    hazard, so it reads as "still recorded after this many volumes". *by*
    splits it on a column — pass a baseline covariate, never a time-varying
    one, since a survivor curve cannot be stratified on something that moves.
    """
    keys = ["tenure_cat"] if by is None else [by, "tenure_cat"]
    g = (panel.groupby(keys)
         .agg(at_risk=("exit", "size"), events=("exit", "sum"))
         .reset_index())
    g["hazard"] = g.events / g.at_risk
    group = [by] if by else []
    g["survival"] = (g.groupby(group)["hazard"].transform(
        lambda h: (1 - h).cumprod()) if group else (1 - g.hazard).cumprod())
    return g


def baseline_connection(panel: pd.DataFrame) -> pd.Series:
    """Whether each firm was connected in the wave it first appears in.

    Survivor curves need a covariate fixed at entry; `connected` is measured
    every wave and moves.
    """
    entry = panel[panel.tenure == 1].set_index("company_id").connected
    return panel.company_id.map(entry).fillna(False)


def survival_sensitivity(processed=None, term: str = "connected") -> pd.DataFrame:
    """The fully controlled hazard ratio under each alternative definition.

    A null that holds only under one coding of the event is not a null. Each
    row re-runs the last specification in :data:`SURVIVAL_SPECS` after
    changing one thing: how the spell ends, which offices count, and whether
    the 1932 entry cohort — drawn from a roster of *quelques* administrators —
    is in the risk set at all.
    """
    variants = {
        "first disappearance (primary)": (False, term, False),
        "permanent exit": (True, term, False),
        "national office only": (False, "national", False),
        "excluding the 1932 entry cohort": (False, term, True),
    }
    rows = []
    for label, (permanent, column, drop_1932) in variants.items():
        panel = survival_panel(processed, permanent_exit=permanent)
        if column == "national":
            panel = panel.assign(connected=panel.n_national > 0)
            column = "connected"
        if drop_1932:
            panel = panel[panel.entry != 1932]
        m = survival_models(panel, column).iloc[-1]
        rows.append({"variant": label, "hr": m.hr, "lo": m.lo, "hi": m.hi,
                     "p": m.p, "n": m.n, "events": m.events})
    return pd.DataFrame(rows)


# --- military service ---------------------------------------------------------
#
# Kept out of `OFFICES` deliberately. Military rank is a different kind of tie
# to the state from a portfolio or a seat in parliament, and folding it into
# `political` would silently change every published rate. It is coded here as
# its own variable; the overlap with civil office is reported, not merged.

#: Ranks by tier. Egyptian ranks are Ottoman: a *ferik* is a lieutenant-general,
#: a *lewa* a major-general, a *miralai* a colonel, a *kaimakam* a
#: lieutenant-colonel, a *bimbachi* a major.
#:
#: *Sirdar* — commander-in-chief of the Egyptian Army — is deliberately absent.
#: Its one occurrence in this corpus is "Grand Cordon Sirdar Ali d'Afghanistan",
#: the Afghan Order of Sardar-i-Ala, which is a decoration.
MILITARY_RANKS: dict[str, re.Pattern[str]] = {
    "general_officer": re.compile(
        r"(?i)\b(?:major|maj|lt|lieut|lieutenant|brigadier|brig)[\.\- ]*gen(?:eral)?\b|"
        r"\bferik\b|\blewa\b|\bliwa\b|\bamiral\b|\badmiral\b"),
    "field_officer": re.compile(
        r"(?i)\b(?:lt|lieut|lieutenant|lient)[\.\- ]*col(?:onel)?\b|\bcolonel\b|"
        r"\bmiralai\b|\bmiralay\b|\bkaimaka[mn]\b|\bbimbach?i\b|\bbimbashi\b|"
        r"\bcommandant\s+(?:de\s+)?(?:l[ae']|the)?\s*\w*\s*(?:armee|army|"
        r"regiment|bataillon)\b"),
    "junior_officer": re.compile(
        r"(?i)\bcapitaine\b|\bcaptain\b|\bbinbachi\b"),
}

#: Service in the armed forces named without a rank.
MILITARY_SERVICE = re.compile(
    r"(?i)\b(?:l['\s]?)?arm[ée]e\s+(?:egyptienne|royale)\b|\begyptian\s+army\b|"
    r"\bforces?\s+fronti[eè]res?\b|\bfrontier\s+districts?\s+administration\b|"
    r"\bminist[eè]re\s+de\s+la\s+guerre\b|\bwar\s+office\b")

#: Phrases that carry a rank word without the rank. "Général" is the whole
#: problem here: in this source it is nearly always *Directeur*, *Consul* or
#: *Secrétaire Général*, and "Commandeur" is a grade of an order, not a
#: command. A captain may also be a ship's master rather than an officer.
MILITARY_EXCLUSIONS = re.compile(
    r"(?i)(?:directeur|consul|secretaire|inspecteur|administrateur|agent|"
    r"assemblee|sequestre|procureur|caisse|president)[\s\-]*gener(?:al|aux)\b|"
    r"\bcommandeur\b|\bcapitaine\s+(?:du\s+port|de\s+navire|marchand)\b")

MILITARY_TIER_LABEL = {
    "general_officer": "General officer",
    "field_officer": "Field officer",
    "junior_officer": "Junior officer",
    "service_no_rank": "Service, no rank printed",
}

#: Tiers ordered from most to least senior.
MILITARY_ORDER = ["general_officer", "field_officer", "junior_officer",
                  "service_no_rank"]


#: Where a following entry evidently begins inside a merged one. Politi prints
#: a rank as an apposition right after the name — "Harari Ralph A, Colonel," —
#: never several directorships later, so a rank beyond this point belongs to
#: the neighbour and not to this director.
_NEXT_ENTRY = re.compile(
    r"(?:\bS\.\s?E\.\s|(?<=\.)\s+(?=[A-Z][a-z]*\s?[a-z]+\s*,))")


def entry_head(name: str, body: str) -> str:
    """The name plus the run of qualifications printed before any directorship.

    Politi prints a military rank as an apposition on the name — "Harari
    Ralph A, Colonel," — among the degrees and decorations, and always before
    the board seats. So the entry is cut at whichever comes first: the point
    where a following entry evidently begins, or the first role word, after
    which everything is directorships and company names.

    **Only for military rank.** Civil office is read from the whole body,
    because Politi writes offices with role words inside them — "Président du
    Sénat", "Vice-Président de la Chambre des Députés" — so this window would
    throw them away.
    """
    from .biographies import _ROLE_RE

    cuts = [m.start() for m in (_NEXT_ENTRY.search(body), _ROLE_RE.search(body))
            if m is not None]
    return f"{name}, {body[:min(cuts)] if cuts else body}"


def find_military(entry: str) -> str | None:
    """The most senior military rank named in one roster entry, or None.

    Returns a tier from :data:`MILITARY_ORDER`. Exclusions are applied first,
    so "Directeur Général", "Commandeur de l'Ordre du Nil" and a harbour
    captain do not code as officers.
    """
    from .biographies import _COMPANY_MARKER

    text = _fold(entry)
    blocked = [(m.start(), m.end()) for m in MILITARY_EXCLUSIONS.finditer(text)]
    # Once a firm name has appeared we are among directorships, and a rank
    # after that point belongs to a neighbouring entry the splitter merged in.
    firm = _COMPANY_MARKER.search(text)
    limit = firm.start() if firm else len(text)

    def live(pattern: re.Pattern[str]) -> bool:
        return any(m.start() < limit
                   and not any(a <= m.start() < b for a, b in blocked)
                   for m in pattern.finditer(text))

    for tier in ("general_officer", "field_officer", "junior_officer"):
        if live(MILITARY_RANKS[tier]):
            return tier
    return "service_no_rank" if live(MILITARY_SERVICE) else None


def military_frame(rosters: dict[int, list[Biography]]) -> pd.DataFrame:
    """One row per (wave, printed entry) with a military rank or service."""
    from .biographies import _COMPANY_MARKER
    from .origin import is_person

    rows = []
    for year, bios in sorted(rosters.items()):
        for bio in bios:
            # A fragment of a firm name captured as an entry sits directly
            # above a real director and would otherwise take his rank.
            if not bio.name or not is_person(bio.name) \
                    or _COMPANY_MARKER.search(bio.name):
                continue
            tier = find_military(entry_head(bio.name, bio.body))
            if tier is None:
                continue
            printed_name = f"{bio.honorific + ' ' if bio.honorific else ''}{bio.name}"
            rows.append({"year": year, "printed_name": printed_name,
                         "tier": tier, "source_page": bio.page,
                         "entry": entry_head(bio.name, bio.body)[:200]})
    return pd.DataFrame(rows, columns=["year", "printed_name", "tier",
                                       "source_page", "entry"])


def attach_military(military: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Resolve the military rows onto `person_id` using the person crosswalk."""
    cols = ["year", "person_id", "tier", "source_page"]
    if military.empty or crosswalk.empty:
        return pd.DataFrame(columns=cols)
    key = (crosswalk[["year", "printed_name", "person_id"]]
           .drop_duplicates(["year", "printed_name"]))
    out = military.merge(key, on=["year", "printed_name"], how="inner")
    return (out[cols].drop_duplicates(["year", "person_id"])
            .sort_values(["year", "person_id"], ignore_index=True))


def military_panel(processed=None) -> pd.DataFrame:
    """The positional panel with military rank and within-wave percentiles.

    Percentiles are computed inside each wave, since a raw centrality is not
    comparable across networks of different size. `military` is False for
    every director with no rank printed, which is a floor in exactly the sense
    the office coding is.
    """
    from pathlib import Path

    from . import config
    from .positional import build_panel

    processed = Path(processed) if processed else config.PROCESSED
    panel = build_panel(processed)
    path = processed / "military_officers.csv"
    if path.exists():
        mil = pd.read_csv(path)
        panel = panel.merge(mil[["year", "person_id", "tier"]],
                            on=["year", "person_id"], how="left")
    else:
        panel["tier"] = np.nan
    panel["military"] = panel.tier.notna()

    aff = pd.read_csv(processed / "affiliations.csv")
    seats = (aff.groupby(["year", "person_id"]).company_id.nunique()
             .rename("seats"))
    panel = panel.merge(seats, on=["year", "person_id"], how="left")
    for col in ("btw_proj", "deg_proj", "seats"):
        panel[f"pct_{col}"] = panel.groupby("year")[col].rank(pct=True) * 100
    return panel


def military_position(panel: pd.DataFrame, n_perm: int = 5000,
                      seed: int = 5) -> pd.DataFrame:
    """Officers' mean within-wave percentile against a within-wave null.

    The null redraws the same number of officers inside each wave, so wave
    size and the concentration of officers in 1950 are held fixed. With
    nineteen officers the null interval is roughly ±10 percentile points:
    read a result inside it as "too few to tell", never as "no difference".
    """
    rng = np.random.default_rng(seed)
    flag = panel.military.to_numpy()
    by_year = {y: np.where(panel.year.to_numpy() == y)[0]
               for y in panel.year.unique()}
    rows = []
    for col in ("pct_seats", "pct_deg_proj", "pct_btw_proj"):
        values = panel[col].to_numpy()

        def gap(mark: np.ndarray, v=values) -> float:
            return v[mark].mean() - v[~mark].mean()

        observed = gap(flag)
        draws = np.empty(n_perm)
        for i in range(n_perm):
            mark = np.zeros(len(panel), bool)
            for indices in by_year.values():
                k = int(flag[indices].sum())
                if k:
                    mark[rng.choice(indices, k, replace=False)] = True
            draws[i] = gap(mark)
        rows.append({"measure": col, "officers": values[flag].mean(),
                     "others": values[~flag].mean(), "difference": observed,
                     "p_perm": float(np.mean(np.abs(draws) >= abs(observed))),
                     "null_lo": float(np.percentile(draws, 2.5)),
                     "null_hi": float(np.percentile(draws, 97.5)),
                     "n": int(flag.sum())})
    return pd.DataFrame(rows)


def office_panel(processed=None) -> pd.DataFrame:
    """The positional panel with within-wave percentiles and the office flags.

    Built on :func:`military_panel`, so the percentile columns and the seat
    count are the same ones the military figure uses and the two are directly
    comparable.
    """
    from pathlib import Path

    from . import config

    processed = Path(processed) if processed else config.PROCESSED
    panel = military_panel(processed)
    path = processed / "person_political.csv"
    cols = [*OFFICES, "political", "national", "all_former"]
    if not path.exists():
        for c in cols:
            panel[c] = False
        return panel
    flags = pd.read_csv(path)
    panel = panel.merge(flags[["year", "person_id", *cols]],
                        on=["year", "person_id"], how="left")
    for c in cols:
        panel[c] = panel[c].fillna(False).astype(bool)
    return panel


def position_by_group(panel: pd.DataFrame, groups: list[str],
                      measures: tuple[str, ...] = ("pct_seats", "pct_btw_proj"),
                      n_perm: int = 4000, seed: int = 9,
                      min_n: int = 3) -> pd.DataFrame:
    """Each group's mean within-wave percentile against a within-wave null.

    The null redraws the same number of members inside each wave, so wave size
    and the group's distribution across waves are held fixed. Read the width
    of the null interval before reading the estimate: `provincial` has ten
    members and a null nearly three times as wide as `parliament`'s.

    Associational. Office and directorship are printed in the same entry, so
    nothing here orders them.
    """
    rng = np.random.default_rng(seed)
    by_year = {y: np.where(panel.year.to_numpy() == y)[0]
               for y in panel.year.unique()}
    rows = []
    for group in groups:
        flag = panel[group].to_numpy().astype(bool)
        if flag.sum() < min_n:
            continue
        for measure in measures:
            values = panel[measure].to_numpy()

            def gap(mark: np.ndarray, v=values) -> float:
                return v[mark].mean() - v[~mark].mean()

            observed = gap(flag)
            draws = np.empty(n_perm)
            for i in range(n_perm):
                mark = np.zeros(len(panel), bool)
                for indices in by_year.values():
                    k = int(flag[indices].sum())
                    if k:
                        mark[rng.choice(indices, k, replace=False)] = True
                draws[i] = gap(mark)
            rows.append({"group": group, "measure": measure, "n": int(flag.sum()),
                         "mean": values[flag].mean(),
                         "others": values[~flag].mean(), "difference": observed,
                         "p_perm": float(np.mean(np.abs(draws) >= abs(observed))),
                         "null_lo": float(np.percentile(draws, 2.5)),
                         "null_hi": float(np.percentile(draws, 97.5))})
    return pd.DataFrame(rows)
