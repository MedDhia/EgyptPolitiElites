# Descriptive figure set

Seven exploratory figures, one PNG each, written to `figures/explore/` by

```
python -m politi explore
```

They are meant for reading the dataset rather than for publication; the
manuscript-style set is specified in `FIGURES_JOURNAL.md`.

## Common construction

**Non-person records are dropped first.** The rosters print decorations,
offices and place names beside names, and a small number of these were captured
as entries. Left in, they rank among the most connected "directors" of the
period — *Grand Officier Couronne Belge* appears against seventeen firms. Every
figure here is built from `explore.real_directors()`, which keeps only rows
whose `person_label` passes `origin.is_person()`. The rule is documented in
`ORIGIN_CODING.md`; it is deliberately conservative, so a handful of genuine
directors with unusual name forms are lost rather than admitting offices.

**1932 is a selection.** Its roster is headed *NOMENCLATURE de quelques
Administrateurs* — some administrators — where the later volumes list them all.
Prominent directors are densely connected by construction, so 1932 sits off the
trend in anything involving seats or connectedness. Figures that are sensitive
to this say so in their own footnote; 1938–1950 are comparable with each other.

**A firm's directors are those the roster named.** The dataset is built from
the person side, so the count of directors attached to a firm is the number of
listed directors who named it, not the size of its board.

## The figures

| File | Question | What it is not |
|---|---|---|
| `seats_per_director.png` | How many board seats did a director hold? | Not a measure of influence: a seat on a small firm counts the same as one on the Banque Misr. |
| `directors_per_firm.png` | How many directors is each firm recorded through? | **Not board size.** See above. |
| `elite_persistence.png` | What share of one wave's directors reappear in the next, raw and per year elapsed? | Not a survival rate: a director absent from a volume may still have been serving. Retention also depends on record linkage across waves, which is probabilistic (`EXTRACTION.md`). |
| `top_brokers.png` | Who held the most distinct directorships across the period? | Not standing in any one year: pooling favours directors who appear in several volumes. Origin is imputed from the name and carries error. |
| `rank_structure.png` | How common were the Pasha and Bey ranks, and did the titled hold more seats? | Rank is recorded as printed, so a promotion appears at the next wave rather than when it happened. Rank was held across every community and is not a proxy for origin. |
| `board_homophily.png` | Did directors sit with their own community more than chance implies? | The null permutes origin labels across directors within the wave, holding board sizes fixed, so compositional shift is already in the null. Pairs are counted only among directors whose origin could be imputed. |
| `firm_turnover.png` | How many waves does a firm appear in, and how much of each wave is new? | Not founding and failure rates: a firm absent from a wave may simply have had no director list it. |

Political connection has its own figure set and its own document:
`POLITICAL_CONNECTIONS.md`, rendered by `python -m politi politics`.

## Dependencies

`top_brokers.png` and `board_homophily.png` need `data/processed/origin_panel.csv`,
produced by `python -m politi origin`. Without it, `politi explore` writes the
other five and says so on stderr.

`board_homophily.png` uses a seeded permutation null (400 draws, seed 1), so it
reproduces exactly.
