#!/usr/bin/env Rscript
# Temporal ERGM for the Egyptian corporate elite network, 1932-1950.
#
# Fitted to the TWO-MODE network. Not to a projection: a one-mode projection
# of an affiliation network makes a clique out of every board, so its
# clustering is arithmetic rather than behaviour. Interlocking appears here as
# b2star(2) on the two-mode graph, which is the same quantity without the
# manufactured dependence.
#
# Composition change is handled by btergm's own adjustment. Each wave's network
# is built on the nodes present in that wave, and btergm intersects the series
# so that memory() compares like with like. That is more conservative than the
# pairwise at-risk restriction used by the Python fit in `politi.tergm`:
# btergm keeps the nodes shared by ALL waves in range, the Python fit keeps
# those shared by each consecutive pair. The script prints the node set it
# actually uses, and the two are not expected to give identical numbers.
#
# The union-plus-NA alternative was tried and abandoned: masking ~4.4 million
# non-existent dyads per wave stores them as missing edges and exhausts memory.
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
office_ids <- unique(persons$person_id[persons$year %in% waves & persons$political == "True"])
if (!length(office_ids)) {
  office_ids <- unique(persons$person_id[persons$year %in% waves &
                                         as.logical(persons$political)])
}
p_office <- ifelse(all_p %in% office_ids, "office", "none")
cat(sprintf("office holders in the union set: %d\n", sum(p_office == "office")))

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
  set.vertex.attribute(n, "origin",
                       c(p_origin[match(p, all_p)], rep("firm", length(f))))
  set.vertex.attribute(n, "office",
                       c(p_office[match(p, all_p)], rep("firm", length(f))))
  set.vertex.attribute(n, "sector",
                       c(rep("person", length(p)), f_sector[match(f, all_f)]))
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
    b1factor("office", base = 2) +             # office holders
    b1nodematch("origin", keep = which(sort(unique(p_origin)) != "unknown")) +
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
