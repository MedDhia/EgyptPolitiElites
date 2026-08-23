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

**Searched result: only 1932 is digitised.** The CEAlex diffusion tree was
probed by full-text search restricted to `bdd.cealex.org`, which indexes the
PDFs themselves — searches return other volumes' contents by their inside text,
so the index is real and the absence is informative. Across a dozen query
formulations, the *Annuaire des sociétés égyptiennes par actions* returns
`LVR_000323` (1932) and nothing else. HathiTrust, Internet Archive,
Bibliotheca Alexandrina and Google Books were searched the same way; none holds
a Politi volume.

| Year | Édition | Place | Online? | Where |
|---|---|---|---|---|
| 1932 | 3 *(inferred)* | Cairo | **yes, full PDF** | `bdd.cealex.org/diffusion/etud_anc_alex/LVR_000323_w.pdf` |
| 1938 | 9 *(inferred)* | Cairo | **no** | print only |
| 1942 | 13 *(inferred)* | Cairo | **no** | print only |
| 1947 | **18** | Alexandria | **no** — catalogue record only | [CEAlex record](https://www.cealex.org/evenement/annuaire-des-societes-egyptiennes-par-actions-alexandrie-1947/) |
| 1950 | **21** | Alexandria | **no** — catalogue record only | [CEAlex record](https://www.cealex.org/evenement/annuaire-des-societes-egyptiennes-par-actions-alexandrie-1950/) |

The 1947 and 1950 CEAlex pages sit under `/evenement/` — announcements of
volumes held or acquired, not digitised items. They carry the édition numbers
(18e, 21e) but no PDF.

### On the édition numbers

Only 1947 (18e) and 1950 (21e) are attested. Both satisfy
`year − édition = 1929`, which implies an unbroken annual run and yields the
inferred numbers above. **This is an inference, not a finding.** Check the
title page before citing an édition number, and correct `EDITIONS` in
`src/politi/config.py` if it is wrong. A break in the run — the war years are
the obvious risk — would shift 1942 and everything after it.

## Getting the four missing volumes

In rough order of effort:

1. **Ask CEAlex directly.** They digitised 1932 and hold the series; a
   researcher request for four further volumes is exactly the kind of thing
   they field. This is the highest-value single email in this project.
2. **AUC Rare Books and Special Collections** (Cairo) — the strongest
   Egyptian-directory holdings outside CEAlex.
3. **IFAO** (Cairo) and **BnF** — both hold Egyptian commercial annuaires;
   BnF will quote for reproduction.
4. **Bibliotheca Alexandrina** — check `dar.bibalex.org` on site; its catalogue
   is not fully exposed to outside search.

Whatever arrives, drop it at `data/raw/politi_<year>.pdf` and the pipeline
takes it from there. Put any new `LVR_` identifier into `EDITIONS` in
`src/politi/config.py` and `fetch` handles the download.

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
