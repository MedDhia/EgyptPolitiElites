"""Assemble the analysis-ready tables from parsed volumes."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import config
from .biographies import Biography, parse_roster
from .names import parse_person
from .parse import Company, parse_volume
from .politics import (attach_military, attach_offices, firm_flags,
                       military_frame, office_frame, person_flags)
from .resolve import Mention, cluster_companies, cluster_persons


# The scanner renders 'l' and 'I' as '|', so a pipe cannot double as the
# delimiter for the name_variants column.
VARIANT_SEP = " ;; "


def load_volume_text(year: int) -> str:
    """Read a wave's extracted text, falling back to the PDF if needed."""
    ed = config.edition(year)
    if ed.text_path.exists():
        return ed.text_path.read_text(encoding="utf-8")
    sources = ed.pdf_sources()
    if sources:
        from .pdftext import extract_pdf

        text = extract_pdf(sources)
        ed.text_path.parent.mkdir(parents=True, exist_ok=True)
        ed.text_path.write_text(text, encoding="utf-8")
        return text
    raise FileNotFoundError(
        f"No source for {year}. Expected a PDF in data/raw/ or data/incoming/ "
        f"(politi_{year}.pdf, or politi_{year}_partNN.pdf), or extracted text "
        f"at {ed.text_path}. See docs/SOURCES.md."
    )


def build_tables(
    volumes: dict[int, list[Company]],
    person_threshold: int = 88,
    company_distance: float = 0.20,
) -> dict[str, pd.DataFrame]:
    """Turn parsed volumes into the five output tables.

    Returns ``affiliations``, ``persons``, ``companies``, ``person_crosswalk``
    and ``company_crosswalk``.
    """
    mentions: list[Mention] = []
    company_meta: dict[tuple[int, str], Company] = {}
    mid = 0
    for year, companies in sorted(volumes.items()):
        for comp in companies:
            company_meta[(year, comp.name)] = comp
            for d in comp.directorships:
                mentions.append(
                    Mention(mention_id=mid, year=year, company=comp.name, role=d.role,
                            order=d.order, person=d.person, page=d.source_page)
                )
                mid += 1

    m2p, people = cluster_persons(mentions, threshold=person_threshold)
    c_pairs = [(y, n) for (y, n) in company_meta]
    m2c, firms = cluster_companies(c_pairs, max_distance=company_distance)

    aff_rows = []
    for m in mentions:
        comp = company_meta[(m.year, m.company)]
        pid = m2p[m.mention_id]
        cid = m2c[(m.year, m.company)]
        aff_rows.append({
            "mention_id": m.mention_id,
            "year": m.year,
            "person_id": pid,
            "person_label": people[pid]["label"],
            "person_printed": m.person.raw,
            "rank": m.person.rank or "",
            "honorific": m.person.prefix or "",
            "company_id": cid,
            "company_label": firms[cid]["label"],
            "company_printed": comp.name,
            "role": m.role,
            "order": m.order,
            "city": comp.city or "",
            "capital_currency": comp.capital_currency or "",
            "capital_amount": comp.capital_amount,
            "source_edition": config.edition(m.year).edition,
            "source_page": m.page,
        })
    affiliations = pd.DataFrame(aff_rows)

    persons = pd.DataFrame([
        {
            "person_id": p["person_id"],
            "label": p["label"],
            "name_key": p["name_key"],
            "highest_rank": p["highest_rank"] or "",
            "n_mentions": p["n_mentions"],
            "years_present": ";".join(str(y) for y in p["years_present"]),
            "n_waves": len(p["years_present"]),
            "name_variants": VARIANT_SEP.join(p["variants"]),
        }
        for p in people.values()
    ])

    companies_df = pd.DataFrame([
        {
            "company_id": c["company_id"],
            "label": c["label"],
            "name_key": c["name_key"],
            "years_present": ";".join(str(y) for y in c["years_present"]),
            "n_waves": len(c["years_present"]),
            "name_variants": VARIANT_SEP.join(c["variants"]),
        }
        for c in firms.values()
    ])
    if not companies_df.empty and not affiliations.empty:
        attrs = (affiliations.sort_values("year")
                 .groupby("company_id")
                 .agg(city=("city", "last"),
                      capital_currency=("capital_currency", "last"),
                      capital_amount=("capital_amount", "last"))
                 .reset_index())
        companies_df = companies_df.merge(attrs, on="company_id", how="left")

    person_crosswalk = pd.DataFrame([
        {"person_id": m2p[m.mention_id], "year": m.year,
         "printed_name": m.person.raw, "display": m.person.display,
         "name_key": m.person.key, "rank": m.person.rank or "",
         "company_printed": m.company, "role": m.role, "source_page": m.page}
        for m in mentions
    ])
    company_crosswalk = pd.DataFrame([
        {"company_id": cid, "year": y, "printed_name": n,
         "name_key": firms[cid]["name_key"]}
        for (y, n), cid in sorted(m2c.items())
    ])

    return {
        "affiliations": affiliations,
        "persons": persons,
        "companies": companies_df,
        "person_crosswalk": person_crosswalk,
        "company_crosswalk": company_crosswalk,
    }


def parse_available(years: list[int] | None = None) -> dict[int, list[Company]]:
    """Parse every wave whose source is present on disk."""
    years = years or list(config.WAVES)
    out: dict[int, list[Company]] = {}
    for y in years:
        if not config.edition(y).has_source():
            continue
        out[y] = parse_volume(load_volume_text(y))
    return out


# --- the biographical roster -------------------------------------------------

def page_map(text: str) -> dict[int, str]:
    """Split page-marked volume text into {page number: body}."""
    parts = re.split(r"<<<PAGE (\d+)>>>", text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def roster_mentions(bios: list[Biography], year: int,
                    start_id: int = 0, firms_only: bool = True) -> list[Mention]:
    """Turn parsed biographies into affiliation mentions.

    The roster is person-side, so each printed entry is already one person —
    which is why it needs no within-volume person resolution, only the
    cross-volume linking every wave gets.
    """
    out: list[Mention] = []
    mid = start_id
    for bio in bios:
        printed = f"{bio.honorific + ' ' if bio.honorific else ''}{bio.name}"
        person = parse_person(printed)
        for pos in bio.positions:
            if firms_only and not pos.is_firm:
                continue
            out.append(Mention(mention_id=mid, year=year, company=pos.organisation,
                               role=pos.role, order=0, person=person, page=bio.page))
            mid += 1
    return out


def parse_rosters(years: list[int] | None = None) -> dict[int, list[Biography]]:
    """Parse the biographical roster of every wave present on disk."""
    years = years or list(config.WAVES)
    out: dict[int, list[Biography]] = {}
    for y in years:
        if not config.edition(y).has_source():
            continue
        bios = parse_roster(page_map(load_volume_text(y)))
        if bios:
            out[y] = bios
    return out


def build_from_rosters(rosters: dict[int, list[Biography]],
                       person_threshold: int = 88,
                       company_distance: float = 0.20,
                       firms_only: bool = True) -> dict[str, pd.DataFrame]:
    """Build the affiliation tables from the biographical rosters."""
    mentions: list[Mention] = []
    for year, bios in sorted(rosters.items()):
        mentions.extend(roster_mentions(bios, year, start_id=len(mentions),
                                        firms_only=firms_only))
    if not mentions:
        return {k: pd.DataFrame() for k in
                ("affiliations", "persons", "companies",
                 "person_crosswalk", "company_crosswalk",
                 "political_offices", "military_officers",
                 "person_political", "firm_political")}

    m2p, people = cluster_persons(mentions, threshold=person_threshold)
    pairs = [(m.year, m.company) for m in mentions]
    m2c, firms = cluster_companies(pairs, max_distance=company_distance)

    aff = pd.DataFrame([{
        "mention_id": m.mention_id,
        "year": m.year,
        "person_id": m2p[m.mention_id],
        "person_label": people[m2p[m.mention_id]]["label"],
        "person_printed": m.person.raw,
        "rank": m.person.rank or "",
        "honorific": m.person.prefix or "",
        "company_id": m2c[(m.year, m.company)],
        "company_label": firms[m2c[(m.year, m.company)]]["label"],
        "company_printed": m.company,
        "role": m.role,
        "order": m.order,
        "city": "",
        "capital_currency": "",
        "capital_amount": None,
        "source_edition": config.edition(m.year).edition,
        "source_page": m.page,
    } for m in mentions])

    persons = pd.DataFrame([{
        "person_id": p["person_id"], "label": p["label"], "name_key": p["name_key"],
        "highest_rank": p["highest_rank"] or "", "n_mentions": p["n_mentions"],
        "years_present": ";".join(str(y) for y in p["years_present"]),
        "n_waves": len(p["years_present"]),
        "name_variants": VARIANT_SEP.join(p["variants"]),
    } for p in people.values()])

    companies = pd.DataFrame([{
        "company_id": c["company_id"], "label": c["label"], "name_key": c["name_key"],
        "years_present": ";".join(str(y) for y in c["years_present"]),
        "n_waves": len(c["years_present"]),
        "name_variants": VARIANT_SEP.join(c["variants"]),
    } for c in firms.values()])

    person_crosswalk = pd.DataFrame([{
        "person_id": m2p[m.mention_id], "year": m.year, "printed_name": m.person.raw,
        "display": m.person.display, "name_key": m.person.key,
        "rank": m.person.rank or "", "company_printed": m.company,
        "role": m.role, "source_page": m.page,
    } for m in mentions])
    company_crosswalk = pd.DataFrame([{
        "company_id": cid, "year": y, "printed_name": n,
        "name_key": firms[cid]["name_key"],
    } for (y, n), cid in sorted(m2c.items())])

    # Political office is read from the same roster entries and resolved onto
    # the person identifiers the linkage just assigned.
    offices = attach_offices(office_frame(rosters), person_crosswalk)
    military = attach_military(military_frame(rosters), person_crosswalk)
    flags = person_flags(offices)
    firm_political = firm_flags(aff, flags)

    return {"affiliations": aff, "persons": persons, "companies": companies,
            "person_crosswalk": person_crosswalk,
            "company_crosswalk": company_crosswalk,
            "political_offices": offices,
            "military_officers": military,
            "person_political": flags,
            "firm_political": firm_political}
