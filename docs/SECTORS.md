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

Share of a director's own seats that are financial:

| Origin | `fin_share` | Any financial seat | n |
|---|---|---|---|
| Arab / Egyptian | 0.142 | 24% | 749 |
| European | 0.130 | 22% | 477 |
| Egyptianised minority | 0.093 | 20% | 834 |

Permuting origin **within each wave**, the spread across the three is 0.049
against a null 95th percentile of 0.044 — p = 0.025.

Treat that as suggestive and no more. It is one borderline p on a max-minus-min
statistic, the three groups are within five percentage points of each other,
and — the substantive point — **this is board seats in Politi's roster, not
ownership, capital or control.** A community could be under-represented on
bank boards and still hold the shares. The finding worth stating is the narrow
one: on the evidence of who sat on financial boards, finance in this period was
not disproportionately a *mutamassirun* preserve, and if anything the
Arab/Egyptian directors were the most exposed to it — which is what the Banque
Misr group would lead one to expect.

## Wording

The same rule as `POLITICAL_CONNECTIONS.md`. Sector and directorship are read
from the same volume, so nothing here orders them, and no statement about a
director's occupation, wealth or control follows from a seat on a bank board.
