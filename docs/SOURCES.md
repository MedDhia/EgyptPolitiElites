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

| Year | Édition | Place | Located? | Lead |
|---|---|---|---|---|
| 1932 | 3 *(inferred)* | Cairo | **direct PDF** | `bdd.cealex.org/diffusion/etud_anc_alex/LVR_000323_w.pdf` |
| 1938 | 9 *(inferred)* | Cairo | not yet | resolve via the CEAlex LVR index |
| 1942 | 13 *(inferred)* | Cairo | not yet | resolve via the CEAlex LVR index |
| 1947 | **18** | Alexandria | catalogue record only | [CEAlex record](https://www.cealex.org/evenement/annuaire-des-societes-egyptiennes-par-actions-alexandrie-1947/) |
| 1950 | **21** | Alexandria | catalogue record only | [CEAlex record](https://www.cealex.org/evenement/annuaire-des-societes-egyptiennes-par-actions-alexandrie-1950/) |

### On the édition numbers

Only 1947 (18e) and 1950 (21e) are attested. Both satisfy
`year − édition = 1929`, which implies an unbroken annual run and yields the
inferred numbers above. **This is an inference, not a finding.** Check the
title page of each volume before citing an édition number, and correct
`EDITIONS` in `src/politi/config.py` if it is wrong. A break in the run — the
war years 1940–45 are the obvious risk — would shift 1942 and everything after
it.

## The main repository: CEAlex

The Centre d'Études Alexandrines runs a digital library, *Études rares et
anciennes sur Alexandrie*, which serves this collection as **OCR'd,
text-searchable PDFs** — which is why the pipeline can use the PDF text layer
directly rather than running OCR from scratch.

- Collection index: <https://bdd.cealex.org/ressources-documentaires/lvr_i.php>
- File pattern: `https://bdd.cealex.org/diffusion/etud_anc_alex/LVR_XXXXXX_w.pdf`

**Next step for 1938, 1942, 1947 and 1950:** open the index, find each
annuaire, read its `LVR_` identifier off the link, and paste it into
`EDITIONS` in `src/politi/config.py`. The `url` field then builds itself and
`python -m politi fetch` will pull all five. Neighbouring identifiers confirm
the collection holds this genre densely (`LVR_000164` = *Annuaire des Juifs
d'Égypte et du Proche-Orient*, 1942; `LVR_000249` = the 1943 volume), so the
missing years are likely to be present.

## Other places to try

- **Google Books** record `OvnmkmUwfIEC` — an *Annuaire des sociétés
  égyptiennes par actions* volume. Snippet view is likely; check.
- **Bibliotheca Alexandrina** (`dar.bibalex.org`) — holds much Egyptian
  francophone print.
- **HathiTrust / Internet Archive** — no record surfaced in searching, but
  neither was searchable from this session.
- **AUC and IFAO libraries** in Cairo hold print runs; CEAlex will answer
  reference queries about its own holdings.

## Adjacent sources worth pairing with Politi

- *Annuaire de la finance égyptienne* (Google Books `IXsUAAAAIAAJ`) — overlaps
  and can be used to cross-check board rosters.
- *Annuaire des Juifs d'Égypte et du Proche-Orient*, 1942 and 1943 (CEAlex
  `LVR_000164`, `LVR_000249`) — biographical enrichment for a community heavily
  represented on these boards.
- *Le Mondain Égyptien* / *The Egyptian Who's Who* — social-register attributes
  (kinship, address, club) to attach to resolved persons.
- *Journal des Tribunaux Mixtes* (CEAlex, `pfe.cealex.org`) — company
  constitutions and board changes between annuaire waves.

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
