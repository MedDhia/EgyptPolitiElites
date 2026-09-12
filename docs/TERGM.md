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

## What this cannot settle

Bootstrapped pseudolikelihood is not MCMC-MLE. It is the estimator `btergm`
uses by default and it is consistent for these purposes, but the usual ERGM
warnings apply: the degree terms are the ones most likely to be misspecified
in a network this sparse (densities run from 1.23% in 1932 down to 0.19% in
1950), and a goodness-of-fit check on the degree distributions of both modes
is part of the script rather than an afterthought.

And the standing limit of the source does not go away. Ties are directorships
*as Politi printed them*. A board he did not print is a zero here, and the
model cannot tell that zero from a seat that was never held.
