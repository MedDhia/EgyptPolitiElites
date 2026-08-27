# Egyptian Corporate Elite Network, 1932–1950

A person–firm affiliation dataset covering the boards of Egyptian joint-stock
companies at five points between 1932 and 1950, machine-extracted from Élie I.
Politi's *Annuaire des sociétés égyptiennes par actions*.

**7,365 directorships · 2,337 directors · 1,987 firms · 5 waves**

---

## Citation

> Hammami, Mohamed Dhia. (2026). *Egyptian Corporate Elite Network, 1932–1950*
> (Version 0.1) [Data set]. https://github.com/MedDhia/EgyptPolitiElites

Author ORCID: [0000-0003-4498-8770](https://orcid.org/0000-0003-4498-8770)

Two fields remain to be filled once the dataset is deposited: a **persistent
identifier** (DOI), which no repository has yet minted for it, and the
**archive** holding the deposit, which should replace the GitHub URL as the
citation target. Until then the URL above is the address of record.

The volumes the dataset is derived from are described in §3 and in
`docs/SOURCES.md`.

---

## 1. Summary

The dataset records which individuals sat on the boards of which Egyptian
joint-stock companies, at five observation points spanning the 1930s
depression, the wartime economy, and the Egyptianisation measures of the late
1940s. It is intended for the study of interlocking directorates, elite
persistence and turnover, and the changing composition of Egypt's corporate
leadership across that period.

Each observation is a **printed directorship**: one named person, one named
company, one volume. Person and company identities are resolved across waves,
so the file supports both cross-sectional and panel analysis.

## 2. Scope and coverage

| | |
|---|---|
| **Unit of analysis** | Directorship (person × firm × wave) |
| **Units of observation** | Individual directors; joint-stock companies |
| **Universe** | Egyptian joint-stock companies (*sociétés anonymes égyptiennes*) and their board members, as listed by the publisher |
| **Geographic coverage** | Egypt (firms domiciled in Egypt; seats principally Cairo and Alexandria) |
| **Temporal coverage** | 1932, 1938, 1942, 1947, 1950 |
| **Time method** | Repeated cross-sections with linked units (unbalanced panel) |
| **Language of source** | French |
| **Mode of collection** | Machine extraction from digitised print, with rule-based parsing and record linkage |

**The universe is the publisher's, not a sampling frame.** Politi covered
registered joint-stock companies. Partnerships, family firms and foreign
companies operating in Egypt without local incorporation are absent, and those
absences are not random with respect to nationality or sector. Coverage also
widens over time: the directors' roster runs 19 printed pages in 1932 and 79 in
1950, so counts track the source's own expansion as well as the economy.

## 3. Source and provenance

The dataset is derived from five volumes of a single annual company register:

> Politi, Élie I. *Annuaire des sociétés égyptiennes par actions*. Alexandria:
> L'Informateur financier et commercial. 3e éd. 1932; 9e éd. 1938; 13e éd.
> 1942; 18e éd. 1947; 21e éd. 1950.

All five were digitised by the Centre d'Études Alexandrines and retrieved from
its *Études rares et anciennes sur Alexandrie* collection. Work using this
dataset should cite the dataset; work quoting or reproducing the volumes
themselves should also cite Politi and credit CEAlex for the digitisation.

| Wave | Édition | Place | CEAlex id | Size | SHA-256 (first 16) |
|---|---|---|---|---|---|
| 1932 | 3e | Alexandria | `LVR_000323` | 64.8 MB | `3c95a0532015b519` |
| 1938 | 9e | Alexandria | `LVR_000191` | 144.0 MB | `f6bd506951954d51` |
| 1942 | 13e | Alexandria | `LVR_000078` | 95.7 MB | `ee9bd0c2b9a83788` |
| 1947 | 18e | Alexandria | `LVR_000173` | 193.3 MB | `467ef51b503bfe15` |
| 1950 | 21e | Alexandria | `LVR_000332` | 208.5 MB | `d816977c3196a711` |

Full digests are in `data/raw/manifest.json`. **The scans are not
redistributed here** — `data/raw/` is version-control ignored — so that any
build can be tied to the exact file it came from without republishing CEAlex's
holdings. `python -m politi fetch` re-downloads them.

Édition numbers for 1932, 1947 and 1950 are attested on the volumes; 1938 and
1942 are inferred from the `year − édition = 1929` offset that the attested
volumes share, and should be verified against their title pages before being
cited. See `docs/SOURCES.md`.

## 4. Collection and processing

Ties are extracted from the section each volume devotes to directors — *Les
Administrateurs des Sociétés Égyptiennes par actions* — an alphabetical roster
in which each entry names one person followed by their positions across firms.
The roster is used in preference to the company-by-company section because it
is person-side: entries are already one per individual, which removes a large
part of the person-disambiguation problem.

Processing runs: PDF → text (embedded layer, or re-OCR where that layer is
defective) → entry segmentation → role and organisation parsing → cross-wave
record linkage → affiliation tables and network exports. `docs/EXTRACTION.md`
documents each stage, including the OCR-tolerant matching used to decide when
two printed firm names denote the same company.

The pipeline is deterministic and fully re-runnable; see §8.

## 5. Files

### Analysis files (`data/processed/`)

| File | Rows | Description |
|---|---|---|
| `affiliations.csv` | 7,365 | **Primary file.** One row per printed directorship, with resolved person and company identifiers, role, rank, and page-level provenance |
| `persons.csv` | 2,333 | Director register: canonical label, highest rank held, waves present, every printed name variant merged into the record |
| `companies.csv` | 1,987 | Firm register: canonical label, waves present, printed name variants |
| `person_crosswalk.csv` | 7,365 | Every person mention and the identifier assigned to it — the audit trail for record linkage |
| `company_crosswalk.csv` | 5,503 | The same for firms |
| `network_summary.csv` | 15 | Wave-level structure: nodes, edges, density, components, mean degree |
| `node_metrics.csv` | 6,272 | Per-node degree, weighted degree, betweenness, eigenvector, closeness |
| `origin_panel.csv` | 3,325 | Person-wave panel with imputed community of origin and per-wave centrality |
| `origin_coefficients_by_wave.csv` | 10 | Estimated origin coefficients by wave |
| `origin_concentration.csv` | 15 | Brokerage shares and within-group Gini, by wave |
| `origin_permutation.csv` | 5 | Within-wave permutation results |
| `political_offices.csv` | 270 | One row per public office a director is recorded in, with whether it is printed as past |
| `person_political.csv` | 225 | Person-wave office flags: seven office types, count, any-office, national-office, all-past |
| `firm_political.csv` | 3,270 | Firm-wave political connection: connected directors, their share, and whether the firm has any |

### Network files (`data/processed/graphs/`)

Fifteen GEXF files (Gephi): per wave, the two-mode affiliation graph, the
firm-by-firm interlock projection, and the director-by-director co-membership
projection. CSV edge lists, GraphML, and pooled multi-wave graphs are produced
by the pipeline but not tracked, to keep the repository to one canonical
serialisation.

### Documentation (`docs/`)

| File | Contents |
|---|---|
| `CODEBOOK.md` | Variable definitions, value labels, controlled vocabularies |
| `SOURCES.md` | Provenance, édition numbering, holdings, rights |
| `EXTRACTION.md` | Processing pipeline, failure modes, the linkage audit procedure |
| `ORIGIN_CODING.md` | Construction and limits of the origin variable |
| `FIGURES_JOURNAL.md` | Figure specifications |
| `FIGURES_EXPLORE.md` | Descriptive figure set: what each one measures and does not |
| `POLITICAL_CONNECTIONS.md` | Office coding: the seven offices, their limits, and what they show |
| `HANDOFF.md` | Transferring source volumes between machines |

## 6. Variables

Full definitions are in **`docs/CODEBOOK.md`**. In outline, `affiliations.csv`
carries the wave, resolved and printed person names, resolved and printed
company names, the position held (controlled vocabulary of fourteen values), the
Ottoman-Egyptian civil rank as printed (`pasha` / `bey` / `effendi` / `agha`),
and the scan page each row was read from.

Three columns — `city`, `capital_currency`, `capital_amount` — are **empty in
the released build**. They belong to the company-by-company section, which is
parsed but not yet merged. They are retained so the schema does not change when
it is.

## 7. Data quality and limitations

Read this section before using the data in an argument.

**Record linkage is probabilistic.** Persons and firms are matched across waves
by rule, not observed identity. Both crosswalk files exist to be audited; the
procedure is in `docs/EXTRACTION.md`. **Run that audit before reporting any
centrality statistic** — a single false merge on a well-connected node
propagates through the whole graph.

**Residual transcription error**, measured on the released build:

| | Count | Share |
|---|---|---|
| Firm names retaining a damaged prefix | 28 | 0.38% of directorships |
| Person records that are company fragments | 5 | 0.21% of persons |
| Non-person records (decorations, offices, places) | 41 | 1.76% of persons |
| Exact duplicate directorships | 19 | 0.26% of directorships |

Each fragments a small number of nodes. The duplicates do not distort the
graphs, which deduplicate by node, but they inflate counts in direct
tabulation. The non-person records are excluded at analysis time by
`politi.origin.is_person`, but are present in the released `persons.csv`; a
user filtering that file directly should apply the same test.

**1932 is not comparable to the later waves.** Its roster is headed
*"NOMENCLATURE de quelques Administrateurs"* — *some* administrators — while
later volumes drop the qualifier and 1942 announces a *"Liste Complète"*. 1932
is therefore a selection of prominent directors, who are densely connected by
construction. Its network statistics run far above the rest (60% of directors
hold multiple seats, against 29–35% later) and that difference is a property of
the list, not of the economy.

**1942 is re-OCR'd, not read from its text layer.** That volume ships a text
layer corrupt enough to collapse its interlock network to a 3.2% largest
component — an artefact that reads as wartime disintegration. Re-OCR from page
images raises it to 35.5%, in line with the other waves.

**Origin is imputed from names**, with 27% of person-wave observations
unclassifiable and the unknowns not missing at random. See
`docs/ORIGIN_CODING.md`.

**Board membership is a formal position.** It proxies influence; it does not
measure it. Nominee and honorific seats were common and are indistinguishable
in this source. Women are near-absent from these boards — a fact about the
source's world, but one worth verifying against the scans before it is
described as a finding.

### Missing data

Missingness is structural rather than item-level: a field is absent when the
volume did not print it. Empty strings denote "not printed"; there are no
imputed values anywhere in the released files. The three capital and city
columns are empty by construction in this build (§6).

## 8. Replication

```bash
pip install -e .

python -m politi sources    # provenance and what is on disk
python -m politi fetch      # retrieve the five volumes from CEAlex
python -m politi extract    # PDF to text (re-OCR where flagged)
python -m politi build --roster   # parse, link, export to data/processed/
python -m politi figures    # network figures
python -m politi origin     # origin analysis and its figure set
python -m politi explore    # descriptive figures, one file each
python -m politi politics   # political-connection figures
```

Python ≥3.10; dependencies pinned in `pyproject.toml`. Re-OCR of the 1942
volume takes roughly 30 minutes; the remaining stages run in minutes. The test
suite (`python -m pytest`, 127 tests) covers name normalisation, parsing
against a synthetic volume in the source's layout, record linkage, network
construction, and figure generation.

Building from the scans reproduces the released files exactly: no stage uses
randomness except the permutation tests, which are seeded.

## 9. Terms of use

**No licence has been selected for this repository.** In the absence of one,
default copyright applies and reuse rights are not granted; a licence should be
added before distribution. Two distinct rights questions arise:

1. **The source scans** are held and distributed by CEAlex under its own terms.
   They are not redistributed here and their terms govern any republication.
2. **The extracted data** are factual records of board composition. Whether the
   compilation attracts protection, and under what terms it should be released,
   is the depositor's decision.

## 10. Version

**0.1** — initial build; all five waves extracted, linked and exported.

Changes to extraction or linkage alter the released tables. Any analysis should
record the commit it was built from, and any published version should be
deposited with a minted identifier.

## 11. Contact

Mohamed Dhia Hammami — compiler and maintainer.
ORCID: [0000-0003-4498-8770](https://orcid.org/0000-0003-4498-8770)
Repository: <https://github.com/MedDhia/EgyptPolitiElites>

A correspondence address should be added here before deposit; most archives
require one alongside the ORCID iD.
