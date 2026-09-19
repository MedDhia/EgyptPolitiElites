#!/usr/bin/env Rscript
# Temporal ERGM for the Egyptian corporate elite network, 1932-1950.
#
# Fitted to the TWO-MODE network. Not to a projection: a one-mode projection
# of an affiliation network makes a clique out of every board, so its
# clustering is arithmetic rather than behaviour. Interlocking appears here as
# b2star(2) on the two-mode graph, which is the same quantity without the
# manufactured dependence.
#
# Composition change is handled by btergm's own adjustment, which conforms each
# time step to the nodes it shares with the previous one. It arrives at exactly
# the pairwise at-risk sets the Python fit in `politi.tergm` constructs by hand
# — 44x109, 152x228, 307x296, 459x427 — so the two are fitted to the same
# dyads and their coefficients are directly comparable.
#
# The union-plus-NA alternative was tried and abandoned: masking ~4.4 million
# non-existent dyads per wave stores them as missing edges and exhausts memory.
#
# Every term emits exactly one statistic. Factor terms are avoided because a
# level absent from one adjusted time step makes them emit different numbers
# of statistics per step, and btergm then fails in rbind. Binary covariates do
# not have that problem.
#
# Inputs are written by `politi.tergm.export_for_r`:
#   data/processed/tergm/tergm_edges.csv    year, person_id, company_id
#   data/processed/tergm/tergm_persons.csv  year, person_id, rank, origin, political
#   data/processed/tergm/tergm_firms.csv    year, company_id, sector
#
# Usage:  Rscript scripts/tergm.R [--from 1938] [--boot 500]
#         Rscript scripts/tergm.R --gof yes [--nsim 100]

suppressPackageStartupMessages({
  library(btergm)
  library(network)
})

args <- commandArgs(trailingOnly = TRUE)
opt <- function(flag, default) {
  i <- match(flag, args)
  if (is.na(i) || i == length(args)) default else args[i + 1]
}
first_wave <- as.integer(opt("--from", "1932"))
n_boot <- as.integer(opt("--boot", "500"))

root <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=",
  commandArgs(FALSE), value = TRUE)[1])), ".."), mustWork = FALSE)
if (!dir.exists(file.path(root, "data"))) root <- "."
indir <- file.path(root, "data", "processed", "tergm")

edges <- read.csv(file.path(indir, "tergm_edges.csv"), stringsAsFactors = FALSE)
persons <- read.csv(file.path(indir, "tergm_persons.csv"), stringsAsFactors = FALSE)
firms <- read.csv(file.path(indir, "tergm_firms.csv"), stringsAsFactors = FALSE)

waves <- sort(unique(edges$year))
waves <- waves[waves >= first_wave]
cat(sprintf("waves: %s   bootstrap replications: %d\n",
            paste(waves, collapse = ", "), n_boot))

# --- node attributes ---------------------------------------------------------
# Attributes are held on the union of nodes and indexed into each wave, so a
# director carries the same origin in every volume he appears in.
all_p <- sort(unique(persons$person_id[persons$year %in% waves]))
all_f <- sort(unique(firms$company_id[firms$year %in% waves]))
np <- length(all_p); nf <- length(all_f)
cat(sprintf("union node set: %d directors x %d firms\n", np, nf))

# Origin is a property of the man. Office is TRUE if recorded in any wave in
# range, which is the floor the annuaire supports.
attr_of <- function(ids, frame, key, column, fallback) {
  sub <- frame[frame$year %in% waves, ]
  sub <- sub[!duplicated(sub[[key]]), ]
  out <- sub[[column]][match(ids, sub[[key]])]
  out[is.na(out)] <- fallback
  out
}
p_origin <- attr_of(all_p, persons, "person_id", "origin", "unknown")
f_sector <- attr_of(all_f, firms, "company_id", "sector", "other")
# Office is WAVE-SPECIFIC, not a property of the man: a director recorded in
# office in 1947 was not necessarily in office in 1938. Collapsing it to
# "ever held office" both widens the group and would no longer match the
# Python fit the R run exists to check.
persons$office <- as.integer(persons$political %in% c("True", "TRUE", "true"))
#: Origin levels the homophily term counts. "unknown" is excluded: directors
#: whose origin could not be imputed are not a community and must not be
#: allowed to match each other.
origin_levels <- c("arab_egyptian", "european", "local_minority")
in_range <- persons$year %in% waves
cat(sprintf("office holders by wave: %s\n",
            paste(sprintf("%d:%d", sort(unique(persons$year[in_range])),
                          tapply(persons$office[in_range],
                                 persons$year[in_range], sum)),
                  collapse = " ")))

# --- one bipartite network per wave -----------------------------------------
# Built on the nodes present in that wave. btergm conforms the series itself.
make_net <- function(y) {
  p <- sort(unique(persons$person_id[persons$year == y]))
  f <- sort(unique(firms$company_id[firms$year == y]))
  m <- matrix(0L, nrow = length(p), ncol = length(f), dimnames = list(p, f))
  e <- edges[edges$year == y, ]
  m[cbind(match(e$person_id, p), match(e$company_id, f))] <- 1L
  n <- network(m, bipartite = length(p), directed = FALSE,
               matrix.type = "bipartite")
  pi <- match(p, all_p); fi <- match(f, all_f)
  # Origin stays categorical: homophily needs it. Everything else is binary,
  # so each term contributes one statistic in every time step.
  set.vertex.attribute(n, "origin",
                       c(p_origin[pi], rep("firm", length(f))))
  wave_office <- persons[persons$year == y, ]
  set.vertex.attribute(n, "office",
                       c(wave_office$office[match(p, wave_office$person_id)],
                         rep(0L, length(f))))
  for (sec in c("finance", "land_property", "agriculture")) {
    set.vertex.attribute(n, sec, c(rep(0L, length(p)),
                                   as.integer(f_sector[fi] == sec)))
  }
  n
}

nets <- lapply(waves, make_net)
names(nets) <- as.character(waves)
for (i in seq_along(nets)) {
  cat(sprintf("  %s: %d directors x %d firms, %d ties\n", names(nets)[i],
              nets[[i]] %n% "bipartite",
              network.size(nets[[i]]) - (nets[[i]] %n% "bipartite"),
              network.edgecount(nets[[i]])))
}

# --- the model ---------------------------------------------------------------
# Only attributes read off the page are covariates. Seat counts, financier
# status and centrality are functions of the ties being modelled, and putting
# any of them on the right-hand side would regress the network on itself.
set.seed(20260912)
model <- btergm(
  nets ~ edges +
    memory(type = "autoregression") +          # a seat held again
    b1star(2) +                                # a director holding two seats
    b2star(2) +                                # two directors sharing a firm
    b1cov("office") +                          # office holders
    b1nodematch("origin", levels = I(origin_levels)) +
    b2cov("finance") + b2cov("land_property") + b2cov("agriculture"),
  R = n_boot, parallel = "no", verbose = TRUE
)

cat("\n==================== TERGM ====================\n")
print(summary(model))

# btergm's confint returns four columns — Estimate, Boot mean, 2.5%, 97.5% —
# so the interval must be selected by name. Taking the first two columns
# silently writes the estimate and the bootstrap mean as if they were bounds.
ci <- confint(model)
pct <- grep("%", colnames(ci))
stopifnot(length(pct) == 2)
out <- data.frame(term = rownames(ci), estimate = coef(model),
                  boot_mean = ci[, "Boot mean"],
                  lo = ci[, pct[1]], hi = ci[, pct[2]], row.names = NULL)
outdir <- file.path(root, "data", "processed")
tag <- if (first_wave > 1932) sprintf("_from%d", first_wave) else ""
write.csv(out, file.path(outdir, sprintf("tergm_coefficients%s.csv", tag)),
          row.names = FALSE)
cat(sprintf("\nwrote %s\n",
            file.path(outdir, sprintf("tergm_coefficients%s.csv", tag))))

# --- goodness of fit -----------------------------------------------------------
# Reported because a TERGM that misses the degree distribution of an affiliation
# network is describing something other than this network.
#
# The statistics are chosen for a BIPARTITE graph:
#   b1deg, b2deg  the two degree distributions -- how many seats a director
#                 holds and how many directors a firm has. These are what the
#                 b1star(2) and b2star(2) terms exist to reproduce, so they are
#                 the direct test of the terms this model leans on.
#   dsp           dyadwise shared partners. In a two-mode network this is the
#                 closure statistic: two directors sharing boards, two firms
#                 sharing directors. The model has NO closure term, and
#                 `docs/EMBEDDEDNESS.md` reports that closure is the largest
#                 predictor of tie formation in this data, so this is where the
#                 specification is most likely to fail -- which is the reason
#                 to look rather than a reason not to.
#   geodesic      the distance distribution, i.e. whether the simulated network
#                 has this one's reach.
#   rocpr         tie prediction, ROC and precision-recall. At a density under
#                 0.5% the PR curve is the informative one; ROC will look good
#                 whatever the model does.
#
# `esp` (edgewise shared partners) is deliberately NOT included. It counts
# partners shared across an existing edge, which requires a triangle, and a
# bipartite graph has none: it would report a column of zeros matched by a
# column of zeros and read as a perfect fit.
if (identical(opt("--gof", "yes"), "yes")) {
  cat("\n---- goodness of fit ----\n")
  nsim <- as.integer(opt("--nsim", "100"))
  set.seed(20260915)
  g <- gof(model, statistics = c(b1deg, b2deg, dsp, geodesic, rocpr),
           nsim = nsim)
  print(g)

  gofdir <- file.path(outdir, sprintf("tergm_gof%s", tag))
  dir.create(gofdir, recursive = TRUE, showWarnings = FALSE)
  # The distribution statistics carry a $stats data frame: observed and
  # simulated mean/median/min/max per level, and a p-value. `rocpr` does not --
  # it holds AUCs and curves instead -- so it is written separately rather than
  # skipped, which an earlier version of this block did silently.
  for (stat in names(g)) {
    entry <- g[[stat]]
    slug <- gsub("^_|_$", "", gsub("[^a-z0-9]+", "_", tolower(stat)))
    if (!is.null(entry$stats)) {
      write.csv(data.frame(statistic = stat, level = rownames(entry$stats),
                           entry$stats, check.names = FALSE),
                file.path(gofdir, sprintf("%s.csv", slug)), row.names = FALSE)
    } else if (!is.null(entry$auc.roc)) {
      # auc.*.rgraph is the same AUC for a random graph of the same density:
      # the baseline the model has to beat. At this density the PR area is the
      # informative one; ROC is high for almost any model.
      write.csv(data.frame(
        statistic = stat,
        measure = c("auc.roc", "auc.roc.rgraph", "auc.pr", "auc.pr.rgraph"),
        value = c(mean(entry$auc.roc), mean(entry$auc.roc.rgraph),
                  mean(entry$auc.pr), mean(entry$auc.pr.rgraph))),
        file.path(gofdir, sprintf("%s.csv", slug)), row.names = FALSE)
    }
  }
  pdf(file.path(gofdir, "gof.pdf"), width = 9, height = 6)
  plot(g)
  dev.off()
  cat(sprintf("\nwrote %s\n", gofdir))
}
