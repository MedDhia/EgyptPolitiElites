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

**Built.** All five volumes are downloaded from CEAlex, parsed, and exported.

| | |
|---|---|
| Directorships | **6,096** |
| Directors | **2,162** |
| Firms | **2,839** |
| Waves | 1932 · 1938 · 1942 · 1947 · 1950 |

The dataset lives in `data/processed/` and is tracked in this repository. The
source scans are not: `data/raw/manifest.json` records a SHA-256 for each
volume so a build can be tied to the exact scan it came from without
redistributing CEAlex's files. `python -m politi fetch` re-downloads them.

### Where the ties come from

Each volume closes with *Les Administrateurs des Sociétés Égyptiennes par
actions* — an alphabetical roster in which each entry is one person followed by
their positions across firms. That roster is the dataset's source, because it
is person-side: entries are already one per person, so the roster performs much
of the entity resolution that the company-by-company section leaves to
inference. `python -m politi build --roster` builds from it.

The company-by-company section is also parsed (`politi.parse`), and carries
seat, capital and balance-sheet detail the roster lacks. It is not yet merged
into the released tables — see **Known gaps** below.

## Quick start

```bash
pip install -e .

python -m politi sources    # what each wave is, and whether it is on disk
python -m politi fetch      # download the annuaire PDFs
python -m politi split      # cut a volume into connector-sized parts
python -m politi extract    # PDF -> text (OCR fallback for bad pages)
python -m politi build --roster   # parse, resolve, export to data/processed/
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

## Known gaps

Read these before using the tables.

- **`city`, `capital_currency` and `capital_amount` are empty.** They come from
  the company section, which is parsed but not yet merged into the released
  tables. The columns are kept so the schema does not change when it is.
- **1942 is thin** — 360 directors against 529 in 1938 and 824 in 1947. That may
  be the volume (96 MB against 144 and 193) or an under-read roster. Check it
  against the scan before treating the dip as a finding.
- **Residual OCR damage.** About 0.4% of firm names still carry a mangled
  prefix ("Conseil d'Administrat.ion Lie the …"), and about 0.2% of person
  records are company fragments the entry-start guard could not catch
  ("Salama Mat•co"). Both fragment a handful of nodes; the crosswalks let you
  find and merge them.
- **Ten directorships are exact duplicates** of another row. They do not
  distort the graphs — both projections deduplicate by node — but they inflate
  row counts if you tabulate `affiliations.csv` directly.
- **Entity resolution is probabilistic.** Run the audit in
  `docs/EXTRACTION.md` before reporting any centrality number.

## Layout

```
src/politi/     config  fetch  pdftext  parse  names  resolve  build  network  export  cli
docs/           SOURCES.md   CODEBOOK.md   EXTRACTION.md   HANDOFF.md
tests/          74 tests, incl. a synthetic volume reproducing Politi's layout
data/           raw/ (ignored)  incoming/ (git hand-off)  interim/  processed/
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests -q
```

`data/raw/` is git-ignored: the scans are CEAlex's to distribute, so the
repository stores SHA-256 digests rather than content.
