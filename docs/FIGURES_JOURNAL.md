# The manuscript's figure set, reproduced for origin

`politi origin` writes these to `figures/journal/` as PDF (the manuscript's
`cairo_pdf` device) with a PNG alongside for screen. The style follows the
manuscript rather than this repository's other figures: `theme_classic` with a
Times-metric serif (Liberation Serif), no in-figure titles because captions
live in the LaTeX, greyscale with firebrick as the single accent, filled
diamonds with horizontal error bars, a dashed grey rule at zero, 6.5 × 4 in.

| Manuscript | Here | Shows |
|---|---|---|
| A2 diagnostics | `fig_diagnostics` | Observed vs fitted, residuals vs fitted, residual density, for log-normal / quasi-Poisson / ZINB |
| A3 baseline coefficients | `fig_baseline_coef` | European coefficient across Linear, Quasi-Poisson, ZIP, ZINB |
| A4 log-normal effects | `fig_lognormal_effects` | Effects as percentage change, with controls |
| A6 permutation | `fig_permutation` | Null from labels shuffled **within wave** |
| A7 centrality comparison | `fig_centrality_compare` | Betweenness vs degree, closeness, clustering, in SD units |
| A8 quantile regression | `fig_quantile` | The coefficient across quantiles of brokerage |
| A9 density | `fig_density_origin` | Brokerage distribution by group, log scale |
| A10 zero centrality | `fig_zero_centrality` | Share with no brokerage at all |
| Lorenz | `fig_lorenz` | Within-group concentration, faceted by wave, Gini printed |
| — | `fig_coef_by_wave` | **Added.** A3's plot run across the five waves |

## Two deliberate departures

**The permutation is stratified by wave.** The manuscript shuffles labels
across the whole network; here the panel pools five networks of different size
and composition, so shuffling across waves would let wave differences leak into
the null. Labels are permuted within wave and the outcome is wave-demeaned, so
only the assignment of origin moves.

**One figure is added.** The manuscript's design is cross-sectional; the
question here is whether the advantage moves over time, so `fig_coef_by_wave`
runs the A3 plot across the waves. Nothing is dropped.

## What A7 says here

In the manuscript, higher local clustering alongside a betweenness deficit is
read as "the structural signature of ties that close existing groups instead of
bridging disconnected ones." That signature appears here on the **European**
side: clustering +0.20 SD (the one interval clear of zero), closeness +0.12,
betweenness −0.09, degree −0.02. Read in the manuscript's own vocabulary,
European directors' ties were comparatively more closed than bridging — the
opposite of the advantage a foreign-capital account would predict.

Also note that the density (A9) and zero-centrality (A10) figures show
distributions that nearly coincide. That is the finding, not a rendering
failure.
