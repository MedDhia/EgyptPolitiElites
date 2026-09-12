#!/usr/bin/env Rscript
# Temporal ERGM for the Egyptian corporate elite network, 1932-1950.
#
# Fitted to the TWO-MODE network. Not to a projection: a one-mode projection
# of an affiliation network makes a clique out of every board, so its
# clustering is arithmetic rather than behaviour. Interlocking appears here as
# b2star(2) on the two-mode graph, which is the same quantity without the
# manufactured dependence.
#
# Composition change is handled by restricting each transition to the dyads
# whose BOTH endpoints are present in consecutive waves. Anything else is
# coded NA and dropped from the pseudolikelihood. This matters: coding an
# absent node's dyads as zero would tell the memory term that a firm which did
# not yet exist had "no tie", which is not the same statement.
#
# Inputs are written by `politi.tergm.export_for_r`:
#   data/processed/tergm/tergm_edges.csv    year, person_id, company_id
#   data/processed/tergm/tergm_persons.csv  year, person_id, rank, origin, political
#   data/processed/tergm/tergm_firms.csv    year, company_id, sector
#
# Usage:  Rscript scripts/tergm.R [--from 1938] [--boot 500]

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

# --- a common node set -------------------------------------------------------
# Every wave's network is built on the union of nodes, so the matrices line up
# and btergm's memory term compares like with like. Presence is tracked
# separately and used to mask.
all_p <- sort(unique(persons$person_id[persons$year %in% waves]))
all_f <- sort(unique(firms$company_id[firms$year %in% waves]))
np <- length(all_p); nf <- length(all_f)
cat(sprintf("union node set: %d directors x %d firms\n", np, nf))

present_p <- lapply(waves, function(y) all_p %in% persons$person_id[persons$year == y])
present_f <- lapply(waves, function(y) all_f %in% firms$company_id[firms$year == y])
names(present_p) <- names(present_f) <- as.character(waves)

# Attributes are fixed at the union level. Origin is a property of the man;
# rank is the highest recorded; office is TRUE if recorded in any wave in
# range, which is the floor the annuaire supports.
attr_of <- function(ids, frame, key, column, fallback) {
  sub <- frame[frame$year %in% waves, ]
  sub <- sub[!duplicated(sub[[key]]), ]
  out <- sub[[column]][match(ids, sub[[key]])]
  out[is.na(out)] <- fallback
  out
}
p_origin <- attr_of(all_p, persons, "person_id", "origin", "unknown")
p_rank <- attr_of(all_p, persons, "person_id", "rank", "untitled")
f_sector <- attr_of(all_f, firms, "company_id", "sector", "other")
office_ids <- unique(persons$person_id[persons$year %in% waves & persons$political == "True"])
if (!length(office_ids)) {
  office_ids <- unique(persons$person_id[persons$year %in% waves &
                                         as.logical(persons$political)])
}
p_office <- ifelse(all_p %in% office_ids, "office", "none")
cat(sprintf("office holders in the union set: %d\n", sum(p_office == "office")))

# --- one bipartite network per wave -----------------------------------------
make_net <- function(y, mask_prev = NULL) {
  m <- matrix(0L, nrow = np, ncol = nf, dimnames = list(all_p, all_f))
  e <- edges[edges$year == y, ]
  m[cbind(match(e$person_id, all_p), match(e$company_id, all_f))] <- 1L
  # A dyad is at risk only if both endpoints exist in this wave, and — when a
  # previous wave is given — in that one too, so memory() is defined.
  ok_p <- present_p[[as.character(y)]]
  ok_f <- present_f[[as.character(y)]]
  if (!is.null(mask_prev)) {
    ok_p <- ok_p & present_p[[mask_prev]]
    ok_f <- ok_f & present_f[[mask_prev]]
  }
  m[!ok_p, ] <- NA
  m[, !ok_f] <- NA
  n <- network(m, bipartite = np, directed = FALSE, matrix.type = "bipartite")
  set.vertex.attribute(n, "origin", c(p_origin, rep("firm", nf)))
  set.vertex.attribute(n, "rank", c(p_rank, rep("firm", nf)))
  set.vertex.attribute(n, "office", c(p_office, rep("firm", nf)))
  set.vertex.attribute(n, "sector", c(rep("person", np), f_sector))
  n
}

nets <- list()
for (i in seq_along(waves)) {
  prev <- if (i == 1) NULL else as.character(waves[i - 1])
  nets[[i]] <- make_net(waves[i], prev)
}
names(nets) <- as.character(waves)
for (i in seq_along(nets)) {
  cat(sprintf("  %s: %d ties on %d dyads at risk\n", names(nets)[i],
              network.edgecount(nets[[i]]),
              sum(!is.na(as.matrix(nets[[i]], matrix.type = "bipartite")))))
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
    b1factor("office", base = 2) +             # office holders
    b1nodematch("origin") +                    # sharing a board with one's own
    b2factor("sector", base = 4),              # finance / land / agriculture
  R = n_boot, parallel = "no", verbose = TRUE
)

cat("\n==================== TERGM ====================\n")
print(summary(model))

ci <- confint(model)
out <- data.frame(term = rownames(ci), estimate = coef(model),
                  lo = ci[, 1], hi = ci[, 2], row.names = NULL)
outdir <- file.path(root, "data", "processed")
tag <- if (first_wave > 1932) sprintf("_from%d", first_wave) else ""
write.csv(out, file.path(outdir, sprintf("tergm_coefficients%s.csv", tag)),
          row.names = FALSE)
cat(sprintf("\nwrote %s\n",
            file.path(outdir, sprintf("tergm_coefficients%s.csv", tag))))

# Goodness of fit on the degree distributions of both modes. Reported because
# a TERGM that misses the degree distribution of an affiliation network is
# describing something other than this network.
if (identical(opt("--gof", "yes"), "yes")) {
  cat("\n---- goodness of fit ----\n")
  g <- gof(model, statistics = c(dsp, esp, geodesic), nsim = 100)
  print(g)
}
