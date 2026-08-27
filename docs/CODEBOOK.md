# Codebook

Five waves: **1932, 1938, 1942, 1947, 1950**. The unit of observation is the
*printed directorship* — one person, one company, one volume.

The released tables are built from each volume's **biographical roster** of
directors (`politi build --roster`), not from the company-by-company section.
The roster is person-side, so each printed entry is already one person. One
consequence matters for anyone reading the schema: **`city`,
`capital_currency` and `capital_amount` are empty**, because those fields exist
only in the company section. The columns are retained so the schema does not
change when that section is merged in.

## `affiliations.csv` — the artefact of record

Everything else in the dataset is derived from this table. One row per printed
directorship.

| Column | Type | Description |
|---|---|---|
| `mention_id` | int | Unique id for this printed occurrence. Stable within a build. |
| `year` | int | Wave (volume year). |
| `person_id` | str | `P#####`. Resolved person, stable across waves. |
| `person_label` | str | Canonical display name (most frequent printed form). |
| `person_printed` | str | The name **exactly as printed**, honorific and rank included. |
| `rank` | str | `pasha` / `bey` / `effendi` / `agha` / empty. As printed *in this volume*. |
| `honorific` | str | Printed prefix (`s.e.`, `m.`, `sir`, …), lowercased. |
| `company_id` | str | `C#####`. Resolved company, stable across waves. |
| `company_label` | str | Canonical company name. |
| `company_printed` | str | Company name as printed in this volume. |
| `role` | str | Controlled vocabulary, below. |
| `order` | int | Position within a company's printed board list. **0 in roster builds**, where entries are ordered by person, not by board. |
| `city` | str | `Cairo`, `Alexandria`, … from the `Siège social` line. **Empty in roster builds.** |
| `capital_currency` | str | `LE` (Egyptian pound), `GBP`, `FRF`, … **Empty in roster builds.** |
| `capital_amount` | float | Nominal capital, not deflated. **Empty in roster builds.** |
| `source_edition` | int | Édition number; inferred for 1932/1938/1942 (see SOURCES.md). |
| `source_page` | int | PDF page the entry was read from. For going back to the scan. |

### `role` vocabulary

| Value | Printed as | In `BOARD_ROLES`? |
|---|---|---|
| `president` | Président, Président du Conseil | yes |
| `honorary_president` | Président d'honneur | yes |
| `vice_president` | Vice-Président | yes |
| `managing_director` | Administrateur-délégué, Administrateur-gérant | yes |
| `director` | Administrateur, Membre du Conseil, Conseiller | yes |
| `general_manager` | Directeur Général | no |
| `manager` | Directeur | no |
| `secretary` | Secrétaire (Général) | no |
| `auditor` | Commissaire aux comptes, Censeur | no |
| `liquidator` | Liquidateur | no |
| `other` | unmatched label | no |

### Roles the roster adds

The roster records positions the company section does not, so these appear in
the released tables alongside the vocabulary above:

| Value | Printed as | In `BOARD_ROLES`? |
|---|---|---|
| `council_member` | Membre du Conseil (not d'Administration) | no |
| `committee_member` | Membre du Comité | no |
| `member` | Membre (of a commission, chamber, bourse) | no |
| `adviser` | Conseiller | no |
| `partner` | Associé | no |
| `delegate` | Délégué | no |

Observed counts across all five waves: `director` 3,193 · `president` 1,019 ·
`managing_director` 647 · `vice_president` 343 · `council_member` 205 ·
`manager` 173 · `member` 156 · `delegate` 87.

### Firms and other bodies

The roster mixes companies with councils, chambers, commissions and government
administrations. Each position is classified, and **only firms are exported by
default**; `politi build --roster --include-bodies` keeps the rest. The
classification is a heuristic over the organisation's name and the role: a
name carrying a company marker (*Société*, *Banque*, *Cy*, *Ltd*, *S.A.E.*) is
a firm; one naming a commission, chamber or *administration des …* is not.
Ambiguous cases follow the role, since "Membre du Conseil …" with no company
marker is usually a public body. Expect errors at the margin, and check
`is_firm`-driven filtering if a specific organisation matters to your argument.

**The default tie definition is board membership**, so `BOARD_ROLES` excludes
executives (`general_manager`, `manager`, `secretary`) and the statutory
auditor (`commissaire aux comptes`), who is an outsider by law. All roles are
*captured*; only the tie definition is narrower. Widen it explicitly:

```python
from politi.network import build_bipartite
g = build_bipartite(rows, roles=frozenset({"president", "director", "auditor"}))
```

Report which definition you used — interlock counts move a lot with it.

## `persons.csv`

| Column | Description |
|---|---|
| `person_id`, `label`, `name_key` | Identity and matching key. |
| `highest_rank` | Highest rank held in any wave (`effendi`<`bey`<`pasha`). |
| `n_mentions` | Total printed directorships across all waves. |
| `years_present`, `n_waves` | Which waves the person appears in. **This is the survival variable.** |
| `name_variants` | Every printed spelling merged into this id. Audit these. |

## `companies.csv`

`company_id`, `label`, `name_key`, `years_present`, `n_waves`,
`name_variants`, plus `city`, `capital_currency`, `capital_amount` carried from
the latest wave in which the firm appears.

## `person_crosswalk.csv` / `company_crosswalk.csv`

Every mention with the id assigned to it. **These exist to be audited.** Sort
`person_crosswalk` by `person_id` and read the `printed_name` values in each
group: a cluster mixing given names is a false merge; two clusters with the
same name are a false split. Hand corrections belong here, upstream of the
network.

## Political office

Three files, all built from the same roster entries as `affiliations.csv`.
Full construction and limits: `POLITICAL_CONNECTIONS.md`.

### `political_offices.csv` — one row per office recorded

| Variable | Type | Definition |
|---|---|---|
| `year` | int | Wave |
| `person_id` | str | Resolved director |
| `office` | str | `cabinet`, `parliament`, `diplomatic`, `provincial`, `judicial`, `court`, `municipal` |
| `former` | bool | Every mention of this office in the entry is printed as past (*ancien*, *ex-*) |
| `source_page` | int | Scan page the entry was read from |

`court` is never populated: the vocabulary appears in the volumes' front matter
but not inside a roster entry.

### `person_political.csv` — one row per person-wave with any office

| Variable | Type | Definition |
|---|---|---|
| `cabinet` … `municipal` | bool | One column per office |
| `n_offices` | int | How many of the seven |
| `political` | bool | Any office |
| `national` | bool | Any of `cabinet`, `parliament`, `diplomatic`, `provincial`, `court` |
| `all_former` | bool | Every office in the entry is printed as past |

**A director absent from this file held no office Politi printed**, which is
not the same as holding none. Treat the absence as `False`, and every rate
built from it as a lower bound.

### `firm_political.csv` — one row per firm-wave

| Variable | Type | Definition |
|---|---|---|
| `n_directors` | int | Directors recorded for the firm in this wave |
| `n_political` | int | How many of them hold any office |
| `n_national` | int | How many hold a national office |
| `share_political` | float | `n_political / n_directors` |
| `connected` | bool | `n_political > 0` |

`n_directors` is the number of directors the roster records for the firm, not
its board size (see **Known limitations**). `share_political` therefore has a
denominator set by the register's coverage, and a firm recorded through one
director is either 0 or 1.

## Network files (`graphs/`)

Per wave, in GEXF, GraphML and CSV:

- `affiliation_<year>` — the two-mode person×company graph. **Analyse this**
  if you can; both projections discard information.
- `company_interlocks_<year>` — firms tied by shared directors. `weight` =
  number shared; `via` = the `person_id`s creating the tie.
- `person_comembership_<year>` — directors tied by shared boards. `weight` =
  number of shared boards.
- `*_pooled` — all waves merged, with `years` plus a `y<year>` boolean per node
  and edge, for filtering in Gephi.

## `network_summary.csv` and `node_metrics.csv`

Wave-level structure (`density`, `components`, `largest_component_share`,
`mean_degree`) and per-node centralities (`degree`, `weighted_degree`,
`betweenness`, `eigenvector`, `closeness`).

**Do not compare density across waves without care.** Density falls
mechanically as a network grows, so if the annuaire covers more firms in 1950
than in 1932, part of any decline is an artefact of coverage. Prefer mean
degree, component structure, or a size-conditioned comparison.

## Known limitations

1. **Coverage is the publisher's, not a sampling frame.** Politi covers
   registered joint-stock companies. Family firms, partnerships and foreign
   companies operating without Egyptian incorporation are absent — and those
   absences are not random with respect to nationality or sector.
2. **Entity resolution is probabilistic.** See `docs/EXTRACTION.md` for the
   failure modes and the audit procedure.
3. **The board is not the firm.** A directorship is a formal position; it
   proxies influence, it does not measure it. Nominee and honorific seats are
   common in this period and are indistinguishable in the source.
4. **Ranks are printed, not dated.** `rank` reflects what the volume printed;
   a promotion appears at the next wave, not when it happened.
5. **Capital is nominal and unindexed**, and wartime inflation between 1942 and
   1947 is severe.
6. **Women are near-absent** from these boards. That is a fact about the
   source's world, but check that the parser is not dropping `Mme`/`Mlle`
   entries before writing about it.
