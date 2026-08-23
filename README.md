# EgyptPolitiElites

Building a corporate elite network dataset from **Élie I. Politi,
*Annuaire des sociétés égyptiennes par actions*** — five waves: **1932, 1938,
1942, 1947, 1950**.

Politi's annual register prints, for every Egyptian joint-stock company, the
full `Conseil d'Administration` with roles and Ottoman-Egyptian ranks. That
makes it the closest thing interwar and wartime Egypt has to a systematic
elite affiliation register, and it supports the standard interlocking-directorate
design across a period spanning the 1930s depression, the war economy, and the
Egyptianisation of the late 1940s.

## Status

The pipeline is **complete and tested** (46 tests). The **source scans are not
in the repository** and had to be left out: the session that built this ran
behind an egress policy that blocked every host except GitHub, so no volume
could be downloaded. `docs/SOURCES.md` records exactly where each of the five
volumes is, including a direct PDF URL for 1932 and the collection index needed
to resolve the other four.

Run `python -m politi fetch` from any machine with ordinary network access and
the dataset builds itself.

## Quick start

```bash
pip install -e .

python -m politi sources    # what each wave is, and whether it is on disk
python -m politi fetch      # download the annuaire PDFs
python -m politi extract    # PDF -> text (OCR fallback for bad pages)
python -m politi build      # parse, resolve, export to data/processed/
```

To see it work without the scans, build from the synthetic fixture:

```bash
python -m politi build --text tests/fixtures/synthetic_volume.txt --year 1932 --out /tmp/demo
```

## What it produces

In `data/processed/`:

| File | Contents |
|---|---|
| `affiliations.csv` | One row per printed directorship. **The artefact of record.** |
| `persons.csv` | Resolved directors, with rank and waves present. |
| `companies.csv` | Resolved firms, with city and capital. |
| `person_crosswalk.csv`, `company_crosswalk.csv` | Every mention and the id it got — for auditing the linkage. |
| `network_summary.csv` | Per-wave density, components, mean degree. |
| `node_metrics.csv` | Per-node degree, betweenness, eigenvector, closeness. |
| `graphs/*.gexf`, `*.graphml`, `*_edges.csv` | Per wave: the two-mode graph, the company interlock projection, the director co-membership projection, plus pooled multi-wave versions. |

GEXF opens directly in Gephi; GraphML in igraph, Cytoscape and NetworkX.

## Design decisions worth knowing before you use it

- **The two-mode graph is primary.** Both projections discard information;
  analyse the affiliation graph where the method allows it.
- **Ranks are data, not noise.** `Pacha`/`Bey`/`Effendi` are stripped from the
  matching key — so a director promoted between waves still matches themselves
  — but retained as a per-wave status variable.
- **Auditors and executives are captured but excluded from the default tie.**
  The `commissaire aux comptes` is a statutory outsider. Widen the definition
  explicitly if your design wants it; see `docs/CODEBOOK.md`.
- **Entity resolution is auditable by construction.** Every merge is written to
  the crosswalks. `docs/EXTRACTION.md` gives the audit script — run it before
  reporting any centrality number.
- **Coverage is the publisher's, not a sampling frame.** Politi covers
  registered joint-stock companies; what is missing is not missing at random.

## Layout

```
src/politi/     config  fetch  pdftext  parse  names  resolve  build  network  export  cli
docs/           SOURCES.md   CODEBOOK.md   EXTRACTION.md
tests/          46 tests, incl. a synthetic volume reproducing Politi's layout
data/           raw/ (git-ignored scans)  interim/ (text)  processed/ (output)
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests -q
```

`data/raw/` is git-ignored: the scans are CEAlex's to distribute, so the
repository stores SHA-256 digests rather than content.
