# Firm sector, and the directors attached to it

## Why this one is different

Office and military rank are printed against a director. Sector is not: it is
a property of the **firms** he sits on. A "financier" here is a director
recorded on at least one bank, insurance company, credit or mortgage house in
that wave — an attribute assembled from the network rather than read off the
page.

That difference creates an arithmetic trap, and it is the single most
important thing about this file.

**Roughly one directorship in eight is on a financial firm.** So a director
with five seats is far likelier to hold one than a director with one seat,
whatever else is true of him. Comparing financiers with everyone else is
therefore mostly comparing the many-seated with the few-seated, and will show
a large "finance effect" built entirely out of seat counts.

Every comparison in `sectors.py` is made **inside wave × seat-count cells**
for that reason. `fin_share` — the share of a director's own seats that are
financial — is the alternative measure, and has no such arithmetic in it.

## Landowners are not in this source

Worth stating before anything else, because the obvious question has a
negative answer. **Politi indexes joint-stock companies, and Egyptian land was
held directly rather than incorporated**, so the landed elite — the class
whose expropriation defined 1952 — is largely invisible here.

Searching every roster entry for landowning vocabulary returns:

| Term | Entries | What they actually are |
|---|---|---|
| *propriétaire* | 27 | Proprietor of a **business**: a yeast factory, *Al-Ahram*, the Hotel Cecil, a chocolate works |
| *propriétaire foncier* | 4 | Two men — Yassine Sirag El Dîne Bey, and Boulad Albert ("propriétaire urbain et foncier") |
| *agriculteur* | 9 | All "Président Honoraire de l'Union des Agriculteurs" — a trade association |
| *domaines* | 43 | All **company** names ("Société Foncière du Domaine de Cheikh Fadl") |
| *feddan*, *izba* | 0 | — |

**Three men across five volumes are printed as landowners.** There is no
person-side landowner variable to build, and none is provided.

Nor is rank a usable proxy. Pasha and Bey did track landholding in this
period, but in this dataset rank is also the marker of office-holding, so
substituting it would make any finding about land indistinguishable from one
about the state. `rank` is in `affiliations.csv` and can be read as rank; it is
not offered as a measure of land.

What *can* be measured is seats on **land and agricultural companies**. That
is a different object: corporate agriculture, not the agrarian elite.

## What is coded

`sectors.FINANCIAL` matches banks (*banque*, *bank*, *banca*, *banco*),
credit and mortgage houses (*crédit*, *hypothécaire*, *mortgage*, *caisse*),
insurers (*assurance*, *réassurance*, *insurance*, *assicurazioni*) and firms
named as financial (*financière*, *finance*, *financial*). `NOT_A_FIRM`
removes ministries, committees and chambers whose names carry one of those
words.

Four kinds of word are left out on purpose:

* ***foncier* and *immobilier*** are land and property, not credit. "Société
  Foncière d'Égypte" is a land company; "Crédit Foncier Égyptien" is a
  mortgage bank and is caught by *crédit*.
* ***land*** and ***estates*** likewise.
* ***bourse*** and ***exchange*** are market institutions, and these labels do
  not reliably separate the securities exchange from the cotton exchange.
* ***trust*** appears nowhere in the corpus.

**The coding is of the firm's printed name.** A bank is named as one; a family
holding company that lent money is not, and is not caught.

235 of 1,985 firms, 393 of 3,220 firm-waves (12.2%), 13.2% of directorships.
Financial firms are recorded through 2.20 directors on average against 2.00
for the rest — a small difference, so the trap above is on the director side,
not the firm side.

## Where land and agriculture sit

175 land-and-property firm-waves (5.4%) and 144 agricultural (4.5%), against
393 financial (12.2%). 322 and 268 person-waves hold at least one such seat.

Co-directors, percentile points above the rest of the wave:

| Sector | Raw | Within wave × seat count | p |
|---|---|---|---|
| Finance | +18.9 | **+6.8** | <0.001 |
| Land and property | +14.9 | +2.2 | 0.18 |
| Agriculture and processing | +15.2 | +3.5 | 0.03 |

The raw gaps are nearly identical across all three, and are mostly seat count.
Inside cells, finance keeps a clear position; land and property does not;
agriculture sits on the boundary and is **one of six tests run on this panel**,
so treat it as unresolved rather than as a finding. Brokerage survives in none
of the three (land +1.2, p = 0.23; agriculture +0.8, p = 0.41).

**A seat on a land company looks much like any other seat of the same rarity.**
Whatever made the agrarian elite powerful in interwar Egypt, it is not visible
in the structure of the corporate network.

### The overlap with office is finance-specific

Mean share of a director's own seats, office holders against the rest:

| Sector | Office holders | Others |
|---|---|---|
| Finance | 0.208 | 0.112 |
| Land and property | 0.053 | 0.053 |
| Agriculture | 0.036 | 0.046 |

Political office went with banking. It did not go with land companies at all,
and agricultural exposure is if anything slightly lower among office holders.

### Exposure by community of origin

Mean share of a director's own seats (%):

| Origin | Finance | Land and property | Agriculture | Land + agriculture |
|---|---|---|---|---|
| Arab / Egyptian | 14.2 | 3.4 | 3.6 | 6.9 |
| European | 13.0 | 3.2 | 2.2 | 5.4 |
| Egyptianised minority | 9.3 | 7.4 | 5.2 | **12.6** |

Permuting origin **within each wave**, the agrarian spread is 0.072 against a
null 95th percentile of 0.030 — p < 0.001. This is a far more robust result
than the corresponding finance spread (p = 0.025), and it runs the other way.

The Egyptianised minorities — Jewish, Greek, Syro-Lebanese — gave the largest
share of their seats to land and agricultural companies and the smallest to
finance; Arab/Egyptian directors were the most finance-exposed. That inverts
the familiar expectation in both directions, and the Banque Misr group on one
side and the Delta land and ginning companies on the other are the obvious
places to look for why.

The same caveat as everywhere here: **these are board seats, not ownership.**
A community under-represented on land-company boards could still hold the
land — and given that Egyptian estates were largely unincorporated, that is
exactly what one should expect to be true of the Arab/Egyptian landowners.

## Where financiers sit

640 person-waves hold at least one financial seat, 19% of directors.

| Measure | Raw | Within wave × seat count | p | Null 95% |
|---|---|---|---|---|
| Co-directors | +18.9 | **+6.8** | <0.001 | ±2.4 |
| Brokerage | +15.6 | +1.2 | 0.08 | ±1.4 |

Percentile points above the rest of the wave, 20 cells, 3,000 permutations
inside each cell.

**A bank seat is a bigger room, not a more between one.** Financial boards are
larger, so holding one puts a director among more people — that survives the
conditioning. Brokerage does not: the people on a bank board already sit with
each other, and a position *between* them does not follow from being among
them.

One-seat cells contribute nothing by construction: **every director holding a
single seat has zero projected betweenness**, so they all tie and the cell
difference is exactly zero.

## The overlap with political office

Not seat-count arithmetic either. Share holding a financial seat:

| Seats held | No office | Public office |
|---|---|---|
| 1 | 10% | 22% |
| 2 | 22% | 34% |
| 3 | 31% | 47% |
| 4 | 52% | 69% |
| 5 or more | 55% | 74% |

Office holders are about twice as likely to hold a financial seat at one seat,
and consistently more likely at every count. Just under half of all office
holders sit on a financial board.

## Financial exposure by community of origin

The full table is under **Exposure by community of origin** above. In short:
`fin_share` runs 0.142 Arab/Egyptian, 0.130 European, 0.093 Egyptianised
minority, and permuting origin within waves gives p = 0.025 on the spread —
borderline, and far weaker than the agrarian spread in the same table.

Treat it as suggestive and no more: one borderline p on a max-minus-min
statistic, with five percentage points between the extremes. The narrow finding
that survives is that on the evidence of who sat on financial boards, finance
was not disproportionately a *mutamassirun* preserve.

## Wording

The same rule as `POLITICAL_CONNECTIONS.md`. Sector and directorship are read
from the same volume, so nothing here orders them, and no statement about a
director's occupation, wealth or control follows from a seat on a bank board.
