# Sourcing the five annuaires

**Status of this document.** Every URL below comes from search-engine results.
The session that compiled it ran behind an egress policy that blocked every
host except GitHub, so **none of these links was opened and verified**. Treat
them as leads to confirm on first download, not as checked citations. The
`fetch` command records a SHA-256 for each file so that whatever you do
download becomes citable.

## The work

Élie I. Politi, *Annuaire des sociétés égyptiennes par actions*, published by
**L'Informateur financier et commercial** (Cairo, later Alexandria). An annual
company register: for each Egyptian joint-stock company it prints the seat,
date of constitution, object, capital structure, the full `Conseil
d'Administration` with roles, the statutory auditors, and a balance sheet. The
board rosters are what make it a network source — it is the closest thing
interwar Egypt has to a systematic elite affiliation register.

## Where each wave stands

**All five volumes are digitised by CEAlex and have been downloaded.**

| Year | Édition | Place | CEAlex id | Size | SHA-256 (head) |
|---|---|---|---|---|---|
| 1932 | 3 | Alexandrie | `LVR_000323` | 64.8 MB | `3c95a0532015b519` |
| 1938 | 9 *(inferred)* | Alexandrie | `LVR_000191` | 144.0 MB | `f6bd506951954d51` |
| 1942 | 13 *(inferred)* | Alexandrie | `LVR_000078` | 95.7 MB | `ee9bd0c2b9a83788` |
| 1947 | 18 | Alexandrie | `LVR_000173` | 193.3 MB | `467ef51b503bfe15` |
| 1950 | 21 | Alexandrie | `LVR_000332` | 208.5 MB | `d816977c3196a711` |

Full digests are in `data/raw/manifest.json`. All five are listed in the
collection index under the author heading **Élie I. POLITI**, together with his
*Indicateur cotonnier d'Égypte* (`LVR_000317`, 105.6 MB, Alexandrie 1932).

### A correction worth recording

An earlier pass through this project concluded that *only* the 1932 volume was
digitised, and wrote that into this file. **That was wrong.** The conclusion
came from full-text search restricted to `bdd.cealex.org`, which returns the
1932 volume and no other — so the absence looked like evidence. It was not:
the search index simply does not cover every PDF in the collection. The index
page itself, once actually fetched, lists all five.

The methodological lesson is worth keeping: a search engine's silence is not
the archive's silence. Read the finding aid before concluding a thing does not
exist.

### On place and édition numbers

All five volumes are published in **Alexandria**, not Cairo — the 1932 title
page reads `IMPRIMERIE A. PROCACCIA / ALEXANDRIE`. An earlier version of this
file said Cairo for the early waves; that is corrected.

The 1932 preface confirms the édition numbering independently: it thanks
readers for the reception of "notre **seconde** édition" and notes that "l'édition
1931 est totalement épuisée", making the 1932 volume the **third**. That fits
`year − édition = 1929`, the offset implied by the two attested numbers (1947 =
18e, 1950 = 21e), so the inferred numbers for 1938 (9e) and 1942 (13e) now rest
on a confirmed pattern rather than an assumption — though they should still be
checked against their own title pages.

## Adjacent volumes that *are* digitised

Confirmed present in the CEAlex diffusion tree (identifiers verified by
full-text search; `config.ADJACENT` holds them):

| Identifier | Volume | Year |
|---|---|---|
| `LVR_000251` | Les Juifs en Égypte | 1938 |
| `LVR_000091` | Le Mondain Égyptien | 1939 |
| `LVR_000055_I/II` | Le Mondain Égyptien | 1941 |
| `LVR_000164` | Annuaire des Juifs d'Égypte et du Proche-Orient | 1942 |
| `LVR_000018_I/II` | Le Mondain Égyptien | 1943 |
| `LVR_000249` | Annuaire des Juifs d'Égypte et du Proche-Orient | 1943 |
| `LVR_000315` | L'Annuaire Mondain | 1950 |
| `LVR_000084_IV` | Egyptian Directory | 1913 |

These land close to the missing waves — 1938, 1941/42, 1943, 1950. **They are
not substitutes.** Politi is a *company* register: its selection rule is
"every registered joint-stock company", which is what makes a clean affiliation
network. *Le Mondain Égyptien* and the *Annuaire des Juifs* are *social and
community* registers: they list persons and often their directorships, so the
network is built from the person side, with a selection rule that is social
standing or community membership rather than incorporation. Interlock measures
from the two genres are not comparable, and mixing them across waves would put
a source change exactly where the historical change is supposed to be.

Used deliberately they are still valuable: as biographical enrichment on
persons resolved from 1932, and as a validity check on name resolution.

## Other leads, now checked

- **Google Books** record `OvnmkmUwfIEC` — an *Annuaire des sociétés
  égyptiennes par actions* volume, year unconfirmed. Snippet view at best; the
  one lead still worth opening by hand.
- **Bibliotheca Alexandrina** (`dar.bibalex.org`) — holds much Egyptian
  francophone print, and its catalogue is not fully exposed to outside search,
  so a null result here is weak evidence. Worth checking on site.
- **HathiTrust / Internet Archive** — searched; no Politi volume. Internet
  Archive's `TheEgyptianWhosWho1941` item matches the phrase only because
  *Le Mondain Égyptien* 1943 mentions Politi's annuaire in its pages.
- **AUC and IFAO** (Cairo) hold print runs.

Two further sources are worth pairing with Politi whatever happens to the
missing waves:

- *Annuaire de la finance égyptienne* (Google Books `IXsUAAAAIAAJ`) — overlaps
  the same firms and can cross-check board rosters.
- *Journal des Tribunaux Mixtes* (CEAlex, `pfe.cealex.org`, digitised) —
  company constitutions and board changes *between* annuaire waves. With only
  1932 in hand this becomes more important, not less: it is the one digitised
  source that can carry board composition forward through the 1930s and 1940s.

## Prior scholarly use

*The Economic Activities of Foreigners in Egypt, 1920–1950: From Millet to
Haute Bourgeoisie*, **Comparative Studies in Society and History** — uses this
family of directories to trace interlocking directorates among foreign
businessmen in Egypt. Worth reading before fixing the coding scheme, since it
sets the standing interpretation this dataset would speak to.

## Rights

The volumes are 1930s–1950s imprints hosted by CEAlex for research use. Check
CEAlex's terms before redistributing the scans. This repository therefore
holds **no** source PDFs: `data/raw/` is git-ignored, and the manifest records
digests rather than content.
