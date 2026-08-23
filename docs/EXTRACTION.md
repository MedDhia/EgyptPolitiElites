# How the extraction works, and where it breaks

## The pipeline

```
PDF ──extract──▶ text ──parse──▶ Company + Directorship
                                        │
                                     resolve  (person / company clustering)
                                        │
                                     build    (affiliations table)
                                        │
                                    network   (two-mode ─▶ projections)
                                        │
                                     export   (CSV, GEXF, GraphML, metrics)
```

## 1. PDF → text (`pdftext.py`)

CEAlex serves the collection as OCR'd, text-searchable PDFs, so the text layer
is read directly with `pdfplumber`. Pages whose text layer holds fewer than 120
characters — usually plates, or pages the original OCR missed — fall back to
Tesseract (`fra`) at 300 dpi, if `pdftoppm` and `tesseract` are installed. Page
markers `<<<PAGE n>>>` are injected so every extracted row keeps a
`source_page` pointing back into the scan.

If a whole volume comes out badly, re-OCR it yourself and drop the result at
`data/interim/politi_<year>.txt`; the parser reads that in preference to the
PDF.

## 2. Text → records (`parse.py`)

A company entry begins with a **capitalised header line**, detected by
requiring >85% of its letters to be uppercase and rejecting a stoplist of
running heads and field labels (`Capital`, `Bilan`, `Sommaire`, …). A block is
kept only if it contains a `Conseil d'Administration` heading or at least one
role label — which is what keeps front matter, indexes and balance-sheet
tables out of the dataset.

Within a block, labelled fields (`Siège social`, `Constituée le`, `Durée`,
`Objet`, `Capital`) are read with line-anchored regexes; the board is sliced at
each role label, and each slice is split into names on commas, semicolons and
`et`, with the `MM.` plural marker and parenthetical glosses
(`(démissionnaire)`) removed.

### Accent folding

OCR of French text drops accents unpredictably, so every structural regex is
written accent-free and matched against a **length-preserving** de-accented
shadow of the text, with offsets sliced out of the original. Length preservation
is the point: it lets the match be accent-insensitive while the captured value
keeps `Palamède` rather than `Palamede`.

### Currency

`£` must never be passed through `unidecode`, which renders it `PS`. French
thousands separators (`L.E. 1.250.000`) are stripped before parsing.

## 3. Names (`names.py`)

Each printed name is decomposed into honorific prefix (`S.E.`, `M.`, `Sir`),
**rank suffix** (`Pacha`/`Bey`/`Effendi` — kept, since rank is a status
variable, not noise), and the name proper.

The name proper is then reduced to a matching key by ordered rewrites designed
for the transliteration variance of French-language Egyptian print:

| Rule | Effect |
|---|---|
| `aou→au`, `ou→u`, `aw→au`, `w→u` | Cattaoui = Cattaui = Qattawi |
| `ch→sh` | Chérif = Sherif |
| `q→k`, `c→k` (`c→s` before *e/i/y*) | Qattawi = Cattaui; Sidqi = Sidky |
| `y→i` | Sidky = Sidki |
| collapse doubled letters | Abboud = Aboud; Nahhas = Nahas |
| drop intervocalic `h` | Nahas = Naas |
| `j→g`, drop trailing `e` | Djemal = Gemal |

**Ordering is load-bearing.** Doubles must collapse *before* intervocalic `h`
is dropped, or `Nahhas` reduces to `Nahas` while `Nahas` reduces to `Nas`.
There is a regression test for exactly this.

The key is aggressive on purpose. It is a **blocking** key for generating
candidates, never an identity claim; `ch→sh` will wrongly fold names where
`ch` is /k/. Linkage is decided in the next stage.

## 4. Resolution (`resolve.py`)

Block on normalised surname → score pairs with a token-sort ratio → gate on
given-name initials → union-find.

The **initial gate** is what stops the largest error in this source: these
boards are full of brothers, fathers and sons sharing a surname. Two mentions
merge only if their given-name initials agree, a bare initial counting as
compatible with any given name starting with it. Where one printed form
abbreviates the other (`J. Cattaui` / `Joseph Cattaui`) the fuzzy score is
unreliable — one key is far shorter — so a token-subset rule merges them
instead, *after* the initial gate has been passed.

### Known failure modes

| Failure | Cause | What to do |
|---|---|---|
| **False merge** of relatives | Same surname *and* same initial (Joseph vs Jacques Cattaui) | Unavoidable from the source alone. Audit `person_crosswalk.csv`; split by hand using company context. |
| **False split** across waves | Heavy OCR damage to a surname, or a changed transliteration the rules miss | Lower `person_threshold`, or merge by hand. |
| **Surname-only mentions** absorb a full name | No initials to gate on | Inspect these; they are listed in `name_variants`. |
| **Company renamed** between waves | Egyptianisation renamed many firms after 1947 | The name-similarity rule will not catch a genuine rename. Link by hand in `company_crosswalk.csv`. |

### The audit you should actually run

```bash
python -m politi build
python - <<'PY'
import pandas as pd
cw = pd.read_csv("data/processed/person_crosswalk.csv")
multi = cw.groupby("person_id")["printed_name"].nunique()
susp = cw[cw.person_id.isin(multi[multi > 2].index)]
susp.sort_values(["person_id", "year"]).to_csv("audit_persons.csv", index=False)
PY
```

Read `audit_persons.csv` by hand. Clusters holding more than two printed forms
are where false merges concentrate. **Do this before reporting any centrality
number** — a single false merge on a hub inflates betweenness across the whole
graph.

## 5. Tuning

```python
build_tables(volumes, person_threshold=88, company_threshold=92)
```

Lower to merge more aggressively (fewer false splits, more false merges);
raise for the opposite. Report whatever you use.

## Adding a wave

Politi ran well beyond 1950. To add a year: put its `LVR_` identifier into
`EDITIONS` in `src/politi/config.py`, then `fetch`, `extract`, `build`. Nothing
else is year-specific.
