# Temporal ERGM

Yes, one is estimable. Three properties of the data decide the specification,
and each of them narrows the claim.

## The model is fitted to the two-mode network

Not to a projection. **A one-mode projection of an affiliation network makes a
clique out of every board**, so its triangles and its transitivity are
arithmetic, not behaviour, and the dependence an ERGM exists to estimate is
already imposed by the construction. Fitting an ERGM to a director
co-membership graph and reporting a triangle term would be reporting board
sizes.

Interlocking is represented instead by `b2star(2)` on the two-mode graph — two
directors sharing a firm. Same quantity, no manufactured dependence.

## Node turnover decides the sample, and the first transition is thin

A memory term lives on the dyads whose **both** endpoints exist in
consecutive waves. Everything else is coded `NA` and dropped: coding an absent
node's dyads as zero would tell the model that a firm which did not yet exist
had "no tie", which is a different statement.

| Transition | Gap | Directors in both | Firms in both | Dyads at risk | Ties before | Ties after | Stable | Formed | Dissolved |
|---|---|---|---|---|---|---|---|---|---|
| 1932→1938 | 6y | 44 | 109 | 4,796 | 88 | 94 | 47 | 47 | 41 |
| 1938→1942 | 4y | 152 | 228 | 34,656 | 247 | 199 | 123 | 76 | 124 |
| 1942→1947 | 5y | 307 | 296 | 90,872 | 374 | 531 | 244 | 287 | 130 |
| 1947→1950 | 3y | 459 | 427 | 195,993 | 719 | 720 | 494 | 226 | 225 |

The first transition is a fortieth the size of the last, and **1932 is a
selection of prominent administrators rather than a full roster**, so it mixes
a change in the annuaire's coverage with a change in the network. Every model
is reported twice: on all five waves, and from 1938.

Note also what the at-risk restriction costs. The full 1950 network has
1,070,176 dyads; the 1947→1950 transition contributes 195,993 of them. The
TERGM is estimated on the persistent core of the elite, not on the whole
register.

## The intervals are unequal

Six, four, five and three years. A TERGM has no offset for interval length, so
**the memory coefficient is an average over four different gaps and is not a
per-year persistence rate.** The earlier life-table analysis
(`POLITICAL_CONNECTIONS.md`) is the place where interval length is handled
properly, by a log-interval offset. `timecov` can let the memory coefficient
vary by transition, which is the most this design allows.

## What may and may not be a covariate

**A quantity computed from the network cannot go on the right-hand side.**
Seat counts, financier status, brokerage and every centrality are functions of
the ties being modelled; including any of them would regress the network on
itself. That rules out most of the variables used elsewhere in this
repository — `financier` in particular, which is defined as "sits on a bank
board" and would be close to circular.

What is left is attributes read off the page:

| Term | Mode | Source |
|---|---|---|
| `b1factor("office")` | director | printed office (`POLITICAL_CONNECTIONS.md`) |
| `b1nodematch("origin")` | director | name-based imputation (`ORIGIN_CODING.md`) |
| `b2factor("sector")` | firm | firm's printed name (`SECTORS.md`) |

Office is printed in the same entry as the directorships, so it is
contemporaneous: the coefficient is an association, and the model orders
nothing. Origin and sector are exogenous to the ties.

## Specification

```
edges                    baseline density
memory(autoregression)   a seat held at t-1, held again at t
b1star(2)                a director holding two seats
b2star(2)                two directors sharing a firm — interlocking
b1factor(office)         office holders' propensity to hold seats
b1nodematch(origin)      sharing a board with one's own community
b2factor(sector)         finance, land, agriculture against the rest
```

## How to run it

The panel is exported from Python and the model is fitted in R with `btergm`,
whose default estimator is pseudolikelihood with bootstrapped confidence
intervals (Desmarais and Cranmer 2012; Leifeld, Cranmer and Desmarais 2018).

```
python -m politi tergm            # writes data/processed/tergm/*.csv
Rscript scripts/tergm.R           # all five waves
Rscript scripts/tergm.R --from 1938 --boot 500
```

Coefficients land in `data/processed/tergm_coefficients.csv`.

## Results

326,317 at-risk dyads carrying 1,544 seats; pseudolikelihood with 300
bootstrap replications over directors.

| Term | All five waves | 95% interval | From 1938 | 95% interval |
|---|---|---|---|---|
| Density (intercept) | −6.67 | −6.85, −6.52 | −6.75 | −6.92, −6.62 |
| **Seat held in the previous wave** | **+6.72** | +6.45, +7.05 | **+6.82** | +6.56, +7.10 |
| Director already holds seats | +0.13 | +0.09, +0.17 | +0.12 | +0.09, +0.16 |
| Firm already has directors | −0.00 | −0.06, +0.06 | +0.02 | −0.04, +0.07 |
| Director holds public office | +0.40 | +0.19, +0.61 | +0.41 | +0.17, +0.63 |
| **Board-mate of the same community** | **+0.30** | +0.21, +0.40 | +0.31 | +0.21, +0.40 |
| Firm is a bank or insurer | +0.11 | −0.09, +0.30 | +0.08 | −0.16, +0.31 |
| Firm is in land or property | +0.29 | +0.03, +0.50 | +0.26 | −0.01, +0.47 |
| Firm is in agriculture | +0.02 | −0.31, +0.29 | +0.04 | −0.28, +0.32 |

**Memory dominates.** A seat held in the previous volume raises the log odds of
holding it again by 6.7, against a density intercept of −6.7. Whatever else
this network is doing, it is mostly keeping people where they were.

Net of memory and of both degree terms, three things survive:

* **A director who already holds seats takes more** (+0.13). Cumulative
  advantage on the person side.
* **A director holding public office is likelier to hold a seat at all**
  (+0.40). Consistent with the office results elsewhere, now with tie
  persistence and both degree distributions held constant.
* **A director is likelier to join a board already seating men of his own
  community** (+0.30). This is the homophily finding from the permutation test
  in `FIGURES_EXPLORE.md` — same-origin pairing 11 to 17 points above a
  random-mixing null — surviving in a model that also controls degree and
  memory. It is the only term significant in every cell of the estimator
  comparison below, and the one result here worth leaning on.

And one negative worth as much as the positives: **firms show no tendency to
accumulate directors** (−0.00, interval straddling zero). Directors accumulate
seats; boards do not accumulate directors. The interlocking in this network is
built from the person side.

Finance is null in this fit, which agrees with `SECTORS.md`: its apparent
advantage was seat count, and seat count is in the model. But btergm finds an
interval for it and the two estimators disagree — see the comparison below
before quoting either. Land and property loses its interval when 1932 is
dropped, so treat it as fragile too.

Nothing here is a direction. Office is printed in the same entry as the
directorships; the coefficient says office holders were likelier to hold
seats, not that office produced them.

## The two estimators side by side

`scripts/tergm.R` (btergm 1.11.1 / ergm 4.12.0) and `politi tergm --fit` are
fitted to the same dyads: btergm's composition adjustment conforms each time
step to the nodes it shares with the previous one, arriving at exactly the
pairwise at-risk sets the Python code builds by hand. The comparison is
therefore a real check, and worth reading for where it fails as much as where
it holds.

All five waves. `*` marks an interval excluding zero.

| Term | btergm | 95% | Python | 95% |
|---|---|---|---|---|
| Density | −6.719 | −6.84, −6.18 * | −6.669 | −6.85, −6.52 * |
| Memory | 6.723 | 5.76, 7.35 * | 6.721 | 6.45, 7.05 * |
| b1star(2) | 0.126 | −0.01, 0.19 | 0.126 | 0.09, 0.17 * |
| b2star(2) | −0.004 | −0.19, 0.08 | −0.004 | −0.06, 0.06 |
| Office | 0.409 | 0.03, 0.53 * | 0.403 | 0.19, 0.61 * |
| Origin match | 0.281 | 0.21, 0.54 * | 0.299 | 0.21, 0.40 * |
| Finance | 0.192 | 0.06, 0.62 * | 0.111 | −0.09, 0.30 |
| Land and property | 0.259 | 0.03, 0.37 * | 0.294 | 0.03, 0.50 * |
| Agriculture | −0.227 | −0.87, 0.04 | 0.023 | −0.31, 0.29 |

From 1938.

| Term | btergm | 95% | Python | 95% |
|---|---|---|---|---|
| Density | −6.807 | −6.85, −6.49 * | −6.752 | −6.92, −6.62 * |
| Memory | 6.816 | 6.13, 7.29 * | 6.817 | 6.57, 7.10 * |
| b1star(2) | 0.118 | 0.01, 0.18 * | 0.118 | 0.09, 0.16 * |
| b2star(2) | 0.019 | −0.08, 0.08 | 0.018 | −0.04, 0.07 |
| Office | 0.414 | −0.09, 0.52 | 0.407 | 0.17, 0.63 * |
| Origin match | 0.286 | 0.22, 0.59 * | 0.306 | 0.21, 0.40 * |
| Finance | 0.106 | 0.03, 0.29 * | 0.081 | −0.16, 0.31 |
| Land and property | 0.237 | 0.05, 0.36 * | 0.259 | −0.01, 0.47 |
| Agriculture | −0.108 | −0.60, 0.04 | 0.037 | −0.28, 0.32 |

**Point estimates agree closely on seven of nine terms** — memory to three
decimals, both degree terms and office to two or three, origin match and land
and property within 0.04. That is a genuine check on the change-statistic
implementation, which is the part most likely to be wrong.

**They diverge on the two thinnest covariates.** Finance and agriculture are
4.5% and 12% of firm-waves, and in the 1932→1938 step there are only 109 firms
at risk in total; agriculture even changes sign between the two, though it is
inside the interval in all four cells and so is null throughout.

**The intervals differ more than the estimates.** btergm's node bootstrap is
markedly wider and right-skewed — its lower bound often sits close to or above
the point estimate — and it is the more conservative of the two. Significance
therefore moves for four terms depending on which estimator is read.

**One term is significant in every cell: origin homophily.** Both estimators,
both wave sets, 0.28 to 0.31. Memory likewise, trivially. Everything else is
contingent on the estimator, the wave set, or both:

| Term | Robust? |
|---|---|
| Memory | Yes — both estimators, both wave sets |
| **Origin match** | **Yes — both estimators, both wave sets** |
| Density | Yes |
| b1star(2) | No — Python both, btergm only from 1938 |
| Office | No — both for all waves, btergm loses it from 1938 |
| Finance | No — btergm both, Python neither |
| Land and property | No — btergm both, Python only all waves |
| b2star(2), Agriculture | Null everywhere |

Read that table before any single coefficient. The homophily finding is the
one this analysis actually supports; the office and person-degree results are
suggestive but estimator-dependent, and the sector terms should not be leaned
on at all.

## Office predicts reach, not persistence

The office coefficient is often misread as a persistence result. It is not:
`memory` and `office` are separate terms, and the model as specified says
nothing about whether a connected director's seat lasts longer.

Asked directly, with a memory × office interaction:

| Term | Estimate | p |
|---|---|---|
| memory | +6.83 | <0.001 |
| office | **+0.65** | <0.001 |
| memory × office | **−0.98** | <0.001 |

The raw numbers behind that: of ties held at t−1, **63.9% of office holders'
seats were held again against 63.5% of everyone else's** (158 and 1,270 ties).
The negative interaction reconciles a higher baseline propensity to hold seats
with identical persistence — it is not office holders losing seats faster.

`change_statistics` computes `memory_x_office`; pass `INTERACTIONS` to
`fit_mple` with `TERMS` to reproduce it.

## What the model contributes: sorting happens at the door

This is the one thing a TERGM does that nothing else in this repository can.
Every other analysis here measures a **state** — who is central, who sits with
whom, who holds what. A TERGM measures **transitions**, and so can be split
into the two processes a cross-section necessarily conflates: what draws a
director onto a board he was not on, and what keeps him on one he was.

`formation_vs_retention` fits the same terms to the dyads empty at t−1 and to
those filled at t−1. `memory` is dropped: it is what defines the two subsets.

| Term | Formation | 95% | Retention | 95% |
|---|---|---|---|---|
| Intercept | −6.996 | −7.17, −6.83 | 0.674 | 0.44, 0.87 |
| Director already holds seats | **+0.199** | 0.17, 0.25 | −0.022 | −0.07, 0.02 |
| Firm already has directors | −0.007 | −0.08, 0.06 | −0.005 | −0.08, 0.08 |
| Director holds public office | **+0.481** | 0.18, 0.74 | 0.083 | −0.30, 0.59 |
| Board-mate of same community | **+0.409** | 0.32, 0.51 | −0.011 | −0.13, 0.12 |
| Firm is a bank or insurer | **+0.378** | 0.16, 0.57 | −0.244 | −0.52, 0.08 |
| Firm in land or property | **+0.460** | 0.18, 0.73 | −0.071 | −0.51, 0.45 |
| Firm in agriculture | 0.211 | −0.20, 0.50 | −0.270 | −0.80, 0.31 |

324,889 dyads carrying 636 new ties; 1,428 dyads carrying 908 retained ones.
Node bootstrap, 100 replications.

**Every covariate that does anything, does it on formation. None does anything
on retention.** Office, homophily, the person-side degree term, finance and
land all carry intervals clear of zero when a seat is taken, and every one of
them collapses to nothing when the question is whether a seat is kept.

The retention nulls are not underpowered. The interval on homophily there is
[−0.13, +0.12], which excludes the formation estimate of +0.41 comfortably;
the person-degree interval is [−0.07, +0.02] against +0.20. These are nulls
with power behind them, not small subsets failing to reach significance.

### What that means

**The elite sorted at the door and not after.** Who got onto a board was
structured by political office, by community, by the seats a man already held
and by what kind of firm it was. Who *stayed* was structured by none of those
things: retention runs at a flat baseline — the intercept of 0.674 is about
two ties kept in three — that no attribute in this model moves.

Three things follow, and they are the contribution:

1. **It dissolves the persistence question.** Office predicts reach and not
   durability (`POLITICAL_CONNECTIONS.md`) because office operates on entry
   only. The same is true of every other covariate. That is not a separate
   finding about office; it is one property of the whole system.
2. **It reconciles the estimator disagreement on finance.** The pooled model
   averaged a formation effect of +0.38 with a retention effect of −0.24 and
   landed near zero with an unstable interval. Split, both halves are legible.
3. **Homophily governs entry, not survival.** The permutation test in
   `FIGURES_EXPLORE.md` established that same-origin *co-presence* exceeds
   chance. It could not say whether same-origin boards form or merely last.
   This says they form.

Note what the retention result does **not** say. Those ties were formed before
t−1, in some cases before 1932, so nothing here shows homophily was absent
when they formed. The claim is narrower: sharing an origin with one's
board-mates does nothing for whether the seat is kept.

### The person–firm asymmetry

`b2star(2)` is null in both halves. **Directors accumulate seats; firms never
accumulate directors**, at entry or afterwards. Whatever produced the
interlocking structure of this network worked through individuals and not
through boards recruiting the well-connected — which is the distinction
between a person-centred and a firm-centred account of interlocking
directorates, and here the data fall on the person side.

This is also the claim that most needs the two-mode network. On a one-mode
projection it could not be asked at all: the projection makes a clique of
every board, so firm-side accumulation is imposed by the construction.

## What this cannot settle

Neither fit is MCMC-MLE: bootstrapped pseudolikelihood is what `btergm` uses
by default, and the Python implementation matches it. The usual ERGM warnings
apply: the degree terms are the ones most likely to be misspecified
in a network this sparse (densities run from 1.23% in 1932 down to 0.19% in
1950), and a goodness-of-fit check on the degree distributions of both modes
is part of the script rather than an afterthought.

And the standing limit of the source does not go away. Ties are directorships
*as Politi printed them*. A board he did not print is a zero here, and the
model cannot tell that zero from a seat that was never held.
