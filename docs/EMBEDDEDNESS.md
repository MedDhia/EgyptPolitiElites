# Embeddedness against structural holes

Two theories of how ties form, both of them claims about **dependence between
ties**, and therefore both invisible to any model that treats dyads as
independent. This is what a TERGM is for.

**Embeddedness** — Granovetter (1985), Uzzi (1996), Gulati (1995). New ties run
where old ties already run, because a prior relation carries information about
the counterparty and a hostage against misbehaviour. In an affiliation network
that means a director joins a board on which he already has a board-mate from
somewhere else. Adding the edge closes a **four-cycle**: he sits on *g*, his
board-mate sits on *g* and on *f*, so *i–g–j–f–i*. The prediction is that the
coefficient on that count is positive.

**Structural holes** — Burt (1992). The return is to *bridging* disconnected
groups; redundant contacts are waste. The prediction usually attributed to Burt
is that the same coefficient is negative — ties reach across holes rather than
fill them in.

**That second reading is too quick, and the test here is in two halves because
of it.** Burt's claim is about **returns**, not about formation: brokers do
better, whoever forms the ties. Closure can govern who joins which board while
brokerage still governs who gains from the boards he is on, and both can hold
at once. So:

1. **The formation half** — does a prior board-mate on a board predict joining
   it? `holes.closure_design`, `holes.fit_closure`, `holes.closure_stratified`.
2. **Burt's half** — do directors in brokerage positions gain seats and survive
   into the next volume more than directors of the same size who are not?
   `holes.brokerage_panel`, `holes.returns_to_brokerage`,
   `holes.brokerage_regression`.

Run both with `politi holes`.

## The design is lagged throughout

Everything on the right-hand side of the formation half is measured at **t−1**.
The main fit in `politi.tergm` follows btergm and computes degree change
statistics on the observed network at t; here the whole specification is
lagged, because a shared board-mate measured at t could have arrived on the
same board in the same volume as the tie being explained. The cost is that
these coefficients are not numerically comparable with those in `TERGM.md`;
the gain is that nothing in the design is contemporaneous with the outcome.

Sample: the same at-risk dyads as the main TERGM — both endpoints present in
consecutive waves — restricted to those **not tied at t−1**, which are the only
ones on which "does a tie form?" is a question. 324,889 dyads, 636 new ties.

## The trap, which on this question has a specific shape

The closure count is `|mates(i) ∩ board(f)|` — the size of an intersection — so
under random matching its expectation is `|mates(i)| × |board(f)| / N`. **Both
factors have to be held fixed, and controlling the director's *seat* count is
not enough.** A man with three seats on large boards has many board-mates and a
high closure count against every firm in the network, behaviour or no
behaviour.

`prior_mates` is in the specification for that reason, next to `prior_board`.
`closure_expected` gives the random-matching benchmark directly, and
`closure_stratified` repeats the comparison inside wave × board-mates ×
board-size cells with a within-cell permutation null, holding the arithmetic
fixed nonparametrically rather than linearly.

This is not a hypothetical. **The brokerage half of this document comes out one
way before the contact-volume control and another way after it**, and the first
version is the one that looks like a finding.

## Formation: closure, decisively

Formation rate by the director's prior distance to the firm. Distance 3 means a
board-mate of his already sits on it.

| Prior distance | Dyads | Formed | Rate per 1,000 | Mean prior seats |
|---|---|---|---|---|
| 3 (a board-mate sits on it) | 7,555 | 102 | **13.50** | 4.29 |
| 5 (two steps out) | 27,004 | 87 | 3.22 | 3.37 |
| 7 or more | 79,589 | 96 | 1.21 | 2.16 |
| unreachable | 210,741 | 351 | 1.67 | 1.64 |

An eleven-fold gradient from distance 3 to distance 7 — but read the last
column: the men at distance 3 hold 4.3 seats on average against 1.6 for the
unreachable. The gradient is confounded with exposure, which is what the model
is for.

Four functional forms, each net of `prior_seats`, `prior_mates`, `prior_board`,
office, origin homophily and the three sector terms. Node-bootstrapped
pseudolikelihood, 100 replications.

| Form of the closure term | Estimate | 95% |
|---|---|---|
| count of shared prior board-mates | **+1.194** | 0.989, 1.502 |
| any shared prior board-mate (binary) | **+1.723** | 1.398, 2.186 |
| log(1 + count) | **+2.224** | 1.825, 2.813 |
| four-cycles, with multiplicity | **+0.733** | 0.556, 1.023 |

The binary form is the easiest to read: a board carrying one of his existing
board-mates has about **5.6 times the odds** of being joined, net of how many
seats he holds, how many board-mates he has and how large the board is.

And nonparametrically, inside wave × board-mates × board-size cells:

| | |
|---|---|
| Raw difference in closure count, formed vs not | +0.174 |
| **Within cells** | **+0.140** |
| Permutation null, 95% band | −0.015, +0.016 |
| p (2,000 within-cell permutations) | < 0.0005 |
| Cells used | 74 |

The within-cell difference is nine times the top of the null band. This is the
strongest single result in the dataset.

### Closure is additive with the rest, not a substitute for it

The obvious suspicion is that closure is community homophily wearing a
different hat: a man joins boards where his board-mates are, and his
board-mates are of his own community, so one term could be absorbing the
other. It is not. The same lagged specification without any closure term
(`holes.fit_baseline`) gives:

| Term | No closure term | With closure |
|---|---|---|
| Board-mate of same community | +0.311 | +0.297 |
| Director holds public office | +0.638 | +0.641 |
| Firm is a bank or insurer | +0.385 | +0.353 |
| Firm in land or property | +0.483 | +0.457 |
| Seats held at t−1 | +0.222 | +0.219 |
| Board-mates at t−1 | −0.043 | −0.060 |
| Closure | — | **+1.194** |

Nothing moves. Community homophily loses 4% of its estimate and the rest
loses less. **Closure and community are separate channels into the same
board**, and the largest term in the model is the one no attribute explains.

### It is not an entity-resolution artefact

The obvious worry in OCR-linked data: if one company were split into two
records, a tie to the twin would look like perfect closure. Of the 102 formed
ties at distance 3, **none** has a board more than 50% identical (Jaccard) to a
board the director already sat on; 78 of 102 are under 25%. The closure is
between distinct boards.

## Burt's half: no return to non-redundancy

Brokerage is measured three ways on the co-membership projection of each wave —
`open_share` (the share of his board-mate pairs who share no board with each
other), Burt's `effective_size`, and Burt's `constraint`. The first two rise
with brokerage, the third falls. Outcomes are measured in the next volume:
`new_seats`, `survives`, `growth`. Multi-seat directors only: a man on one board
has every alter pair connected through that board, so his `open_share` is 0 by
construction.

**A projection is used here, and only as a measure.** That is not the thing this
repository refuses. Fitting an ERGM to a projection is illegitimate because the
projection manufactures a clique per board and the model would estimate that
arithmetic as dependence. Measuring how redundant a man's contacts are has no
such problem — though it inherits the same clique structure, which is the next
point.

### Stratified by seat count, it looks like a Burt effect

| Brokerage measure | Outcome | Within cells | p | Null 95% |
|---|---|---|---|---|
| `open_share` | new seats | **+0.49** | **0.003** | −0.35, +0.34 |
| `effective_size` | new seats | +0.32 | 0.067 | −0.36, +0.33 |
| `constraint` (reversed) | new seats | +0.29 | 0.103 | −0.35, +0.34 |
| any | survives | +0.03 to +0.06 | 0.21–0.53 | — |
| any | seat growth | −0.33 to −0.39 | 0.14–0.22 | — |

The direction is the same in all four waves. Reported at this point, it would
read: brokers acquire more seats.

### Holding contact volume fixed, it is gone

Burt's distinctive claim is not that more contacts help — Coleman's closure
account predicts that too. It is that **non-redundant** contacts help *at a
given number of contacts*. So the board-mate count belongs in the model.
Poisson, cluster-robust by director, wave fixed effects, seat count as a
factor, 560 person-waves:

| Model | Term | Coefficient | 95% | p |
|---|---|---|---|---|
| seats only | `open_share` | +0.566 | −0.310, +1.443 | 0.205 |
| seats + volume | `mates` | **+0.035** | +0.018, +0.052 | **<0.001** |
| | `open_share` | +0.220 | −0.646, +1.085 | 0.619 |
| seats only | `effective_size` | **+0.041** | +0.025, +0.057 | **<0.001** |
| seats + volume | `mates` | −0.047 | −0.156, +0.061 | 0.392 |
| | `effective_size` | +0.091 | −0.027, +0.208 | 0.130 |
| seats only | `constraint` | −0.732 | −1.820, +0.357 | 0.188 |
| seats + volume | `mates` | **+0.037** | +0.019, +0.055 | **<0.001** |
| | `constraint` | +0.076 | −0.853, +1.006 | 0.872 |

**The board-mate count carries the association; the structure of those contacts
adds nothing.** The nonparametric version agrees: stratifying by wave × seats ×
board-mate bin instead of wave × seats moves `open_share` from +0.40 (p = 0.02)
to +0.10 (p = 0.68).

One honest limit. `effective_size` correlates **0.979** with the raw board-mate
count in this network, so the model cannot separate them and its p = 0.130 is
not evidence either way. That correlation is itself the point: **in an
affiliation network Burt's effective size is close to a relabelling of degree.**
Boards are cliques, so the alters a director meets on one board are wholly
redundant with each other, and subtracting redundancy leaves roughly the number
of boards. The measures with content independent of volume are `open_share`
(r = 0.51) and `constraint` (r = −0.67), and both are flat.

## What the two halves say together

**Ties form by closure; the payoff does not go to bridging.** A director reaches
a new board through a man he already sits with, and what predicts his
acquiring seats is how many such men he has — not whether they are drawn from
unconnected worlds.

Both halves point the same way, which is worth saying because they did not have
to. Burt's theory survives a negative formation coefficient perfectly well —
bridging ties can be rare and still be the valuable ones. What it does not
survive is bridging ties being neither more common nor more rewarded. In this
network they are neither.

Read against `TERGM.md`, this sharpens the "sorting at the door" result. Every
covariate there loaded on formation and none on retention, and closure is the
largest of them: the door is opened by an existing board-mate. Office, community
and sector are attributes a man brings to that door; closure is the mechanism
that admits him.

## Limits

* **Association, not direction.** See the Wording section below. Closure is
  measured at t−1 and the tie at t, so the temporal order is clean, but nothing
  rules out a third thing — a family, a bank, a quarter of Cairo — producing
  both the prior board-mate and the new seat. A lag is not an instrument.
* **No firm-side agency.** The design asks which board a director joins. It
  cannot tell a director seeking a board from a board recruiting a director,
  and the language should not imply either.
* **Board-mates are not acquaintances.** Two men printed on the same board may
  never have met. Co-presence on a page is the tie; treat the trust mechanism as
  a hypothesis the data is consistent with, not one it demonstrates.
* **Brokerage is measured on a projection** and inherits every linkage error in
  it, amplified: a wrongly merged pair of directors creates spurious contacts.
* **Returns are measured over unequal intervals** — 6, 4, 5 and 3 years — and
  `new_seats` is a count over that gap, so the wave fixed effects are doing
  real work and the coefficients are not per-year rates.
* **Reverse coverage risk on `open_share`.** A director whose other boards are
  printed without their full membership scores 0, so the measure is part
  structure and part page. This is a further reason the mates-controlled result
  is the one to report.

## Wording

Same rule as `POLITICAL_CONNECTIONS.md` and `SECTORS.md`.

* Write "boards carrying an existing board-mate are more often joined", not
  "prior ties brought new seats" or "trust produced the appointment".
* Write "the board-mate count is associated with seat acquisition; the
  non-redundancy of those contacts is not", never "brokerage does not pay".
  The finding is about this network, these measures and these five volumes.
* A control that removes an association shows the association was not
  independent of the control. It does not show the control is the cause.
* `effective_size` in an affiliation network is near-collinear with degree.
  Do not report it as a structural finding without saying so.
