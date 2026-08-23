"""Assemble the analysis-ready tables from parsed volumes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .parse import Company, parse_volume
from .resolve import Mention, cluster_companies, cluster_persons


def load_volume_text(year: int) -> str:
    """Read a wave's extracted text, falling back to the PDF if needed."""
    ed = config.edition(year)
    if ed.text_path.exists():
        return ed.text_path.read_text(encoding="utf-8")
    if ed.pdf_path.exists():
        from .pdftext import extract_pdf

        text = extract_pdf(ed.pdf_path)
        ed.text_path.parent.mkdir(parents=True, exist_ok=True)
        ed.text_path.write_text(text, encoding="utf-8")
        return text
    raise FileNotFoundError(
        f"No source for {year}. Expected {ed.pdf_path} or {ed.text_path}. "
        f"See docs/SOURCES.md for where to obtain the volume."
    )


def build_tables(
    volumes: dict[int, list[Company]],
    person_threshold: int = 88,
    company_threshold: int = 92,
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
    m2c, firms = cluster_companies(c_pairs, threshold=company_threshold)

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
            "name_variants": " | ".join(p["variants"]),
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
            "name_variants": " | ".join(c["variants"]),
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
        ed = config.edition(y)
        if not (ed.pdf_path.exists() or ed.text_path.exists()):
            continue
        out[y] = parse_volume(load_volume_text(y))
    return out
