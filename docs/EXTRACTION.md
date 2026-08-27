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

### The 1942 volume ships a defective text layer

The short-page fallback catches pages with *no* text. It does not catch a page
whose text is present, long, and wrong — which is what the 1942 scan has
throughout. There, "Société" reads as `Sociétt'l`, "Banque Belge et
Internationale" as `Banquf' Belge Pl Tnlernationale`. Every mention of a firm
is corrupted differently, so no two mentions match, and the wave's interlock
network collapses into isolated fragments.

The damage was not obvious in the counts. 1942 had a normal share of
multi-board directors (33%, against 33% in 1938 and 35% in 1947) — the ties
were being read, they simply could not be linked. What gave it away was the
largest connected component: **3.2%, against 46-62% in every other wave**. Read
as history that would have said the wartime corporate network disintegrated.
It was an artefact.

Re-OCR'ing the volume from its page images fixes it:

| | text layer | re-OCR |
|---|---|---|
| Directors | 360 | **719** |
| Interlock edges | 556 | **1,774** |
| Largest component | 3.2% | **35.5%** |

`config.EDITIONS[1942].bad_text_layer` records this, so `politi extract`
re-OCRs that volume automatically. `--force-ocr` does the same for any volume.
It costs about 30 minutes for a 680-page scan.

**The general lesson:** a plausible network statistic can be produced entirely
by OCR quality. Before reading a cross-wave difference as history, check that
the waves are of comparable transcription quality. Component share is a useful
canary — it collapses long before the raw counts look wrong.

If a whole volume comes out badly, you can also re-OCR it yourself and drop the
result at `data/interim/politi_<year>.txt`; the parser reads that in preference
to the PDF.

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

## 4b. Matching company names through the scanner

The hardest part of this dataset is deciding when two printed names are the
same firm. Politi prints "The Kafr El Zayat Cotton Co", "Kafr el Zayat Collan
Co" and "Kafr El Zay at CoLLan Co" for one company — and "Kafr El Zayat Land
Co" for a different one.

**A similarity threshold cannot do this.** Measured on this corpus, the same
firm ("Compagnie Générale Égyptienne de Pétroles" against its mangled twin)
scores **88.5** by plain ratio, while those two *different* firms score
**87.5**. The distributions overlap, so any cutoff either merges Cotton with
Land or splits Cotton from Collan. Four mechanisms are used instead.

**1. The OCR skeleton, for exact matching.** Each character is folded into the
class the scanner confuses it with — l/t/i/1, c/e/o/a, n/u/m/h — and spaces are
dropped, since the scanner inserts them inside words. Collan, CoLLan and Cotton
become one string; Land stays another, because l/t and a/o are confusable while
l/c and n/t are not. This is precise, and it does most of the work.

**2. A weighted edit distance, for the rest.** Substituting a character for one
it is commonly misread as costs 0.3; any other substitution costs 1.0. The same
firm scanned twice differs by many *cheap* edits, two firms by few *expensive*
ones — which is exactly the signal a plain ratio throws away. Collan/Cotton
scores 0.053, Cotton/Land 0.271; the merge threshold is 0.20.

The skeleton is used only for exact matching, never fuzzy. Folding is lossy
enough that unrelated short words collide: an earlier attempt to snap rare
tokens onto frequent ones by skeleton similarity proposed "louis" → "toutes"
and "benoist" → "bomonti".

**3. Complete linkage.** Single-linkage union-find chains A~B~C into one
cluster even when A and C are unrelated; that is how "Alexandria Life
Insurance" was absorbed into "Alexandria Insurance". Every cross-pair must now
stay within a 0.30 diameter.

**4. An unmatched-word veto.** A scanner mangles words, it does not invent
them, so a whole extra content word means a different firm however small the
edit distance — "Life" is four letters but decisive. The veto is suspended
when two names are already near-identical (≤0.10), because there an odd token
is debris: OCR splits "Alexandria" into "A lexandria", and the stray "A" would
otherwise read as a missing word.

Together these take the 1932-1950 corpus from 3,052 company nodes to 1,987
without merging any of the firms above. Residual singletons are names damaged
past rule-based repair ("Tl1e Alexandria Insurance Co"); the crosswalk is where
you merge those by hand.

### Repairing the structural vocabulary

Separately, the words that carry an entry's *grammar* — Administration,
Conseil, Membre, Président — are repaired by fuzzy skeleton match before
parsing, so "Aaministration", "Adrmnistration" and "ACministrateur" are read as
what they plainly are. This is confined to that vocabulary and applied only to
the entry body: personal names are left exactly as printed, since a name is the
one place a French word is not expected and repairing there turns "Achille"
into "Comité". `printed` always keeps the entry as scanned.

## 5. Tuning

```python
build_from_rosters(rosters, person_threshold=88, company_distance=0.20)
```

`company_distance` is a *distance*: raise it to merge more aggressively,
lower it to split. `cluster_companies` also takes `max_diameter` (0.30) and
`near_identical` (0.10). Report whatever you use.

## Adding a wave

Politi ran well beyond 1950. To add a year: put its `LVR_` identifier into
`EDITIONS` in `src/politi/config.py`, then `fetch`, `extract`, `build`. Nothing
else is year-specific.
