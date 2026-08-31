# Political connection

## What is coded

Politi's roster does not only list board seats. Alongside them it prints the
public offices a director held or had held:

```
S.E. Sadek, Wahba (Pacha), Sénateur; ancien Ministre; Vice-Président …
S.E. Abdel Rahman el Bialy Bey, Ancien Ministre des Finances, Président …
… Ministre des Wakfs, député de Bassioun, Ex-Gouverneur du …
```

`politi build --roster` reads those lines and writes three tables.

| File | Unit | Contents |
|---|---|---|
| `political_offices.csv` | person-wave-office | One row per office a director is recorded in, with `former` and the scan page |
| `person_political.csv` | person-wave | The seven office booleans, `n_offices`, `political`, `national`, `all_former` |
| `firm_political.csv` | firm-wave | `n_directors`, `n_political`, `n_national`, `share_political`, `connected` |

### The seven offices

| Code | Covers |
|---|---|
| `cabinet` | A portfolio, the premiership, an under-secretaryship of state |
| `parliament` | Chamber of Deputies, Senate |
| `diplomatic` | Ambassador, consul-general, envoy, *ministre plénipotentiaire*, *ministre d'Égypte à …* |
| `provincial` | Governor of a governorate or city, *moudir*, *mouhafez* |
| `judicial` | Bench, Conseil d'État, *parquet*, Mixed Courts |
| `court` | Royal household: chamberlain, royal cabinet |
| `municipal` | Municipal council or commission |

`national` is any of `cabinet`, `parliament`, `diplomatic`, `provincial`,
`court`. `political` is any of the seven.

**No `court` office is coded in any wave.** The vocabulary is retained because
the word appears in the volumes' front matter, but never inside a roster entry.

## Three things the coding is not

**It is a floor, not a census.** Politi printed an office when he had it. A
director with none coded may simply have had none recorded. Every rate is a
lower bound, and change across waves is change in the annuaire's editorial
practice as much as in who sat on boards. The comparison that survives this is
*within* a wave: office holders against everyone else in the same volume, under
the same practice.

**Most offices are past.** Between 9% and 35% of office holders per wave have
every office printed as *ancien* or *ex-*; `all_former` records it. A former
minister is a political connection — arguably a better one, since he is free to
take board seats — but he is not a serving official, and the two must not be
conflated.

**"Ministre" is two different jobs.** *Ministre des Finances* is a cabinet
post; *Ministre Plénipotentiaire* and *Ministre d'Égypte à Paris* are
diplomatic ranks. `politics.EXCLUSIONS` separates them. Conflating them would
roughly double the apparent size of the cabinet-connected group. The same
mechanism keeps the Governor of the National Bank and a Rotary district
governor out of `provincial`.

## Offices are not names

An office printed against a name — `Sadek Wahba Pacha Sénateur`,
`Abdel Haï Khalil Bey Député` — is not part of the name, and the name/body
splitter no longer keeps it. `biographies._NAME_TAIL` strips a trailing office,
decoration or *ancien* qualifier, and the office is recovered here as data.
This matters beyond tidiness: those suffixes defeated the origin classifier, so
directors with offices were disproportionately coded `unknown`. Removing them
raised the Arab/Egyptian office-holding rate from an artefactually low figure to
its true one.

Never strip the first token: a surname may be *Chevalier*.

## What the coding shows

Rendered by `python -m politi politics` into `figures/politics/`.

| File | Finding |
|---|---|
| `office_holders.png` | About one director in sixteen is recorded in a public office; parliament and cabinet dominate |
| `office_and_seats.png` | Office holders are recorded on 2.3–2.4× as many boards (1938 onward) |
| `connected_firms.png` | 15–25% of firms had at least one connected director |
| `office_by_origin.png` | Office holding is concentrated among Egyptian directors: 17.2% against 2.3% of Europeans |
| `office_position.png` | The raw brokerage gap largely closes once seat count is held constant: office is associated with more seats, not with a more central position per seat |
| `origin_adjusted.png` | The origin coefficients are essentially unchanged by holding office constant |
| `firm_persistence.png` | Connected firms reappear more often in the raw data, and the gap is accounted for by how many directors the register records for them |
| `firm_survival.png` | Discrete-time survivor function and hazard of leaving the register: the hazard falls steeply with tenure, and connection is not distinguishable from none once coverage is held constant |
| `military_officers.png` | Every director with a military rank, by within-wave brokerage percentile: officers sit at the middle of the distribution |

## Are politically connected firms more likely to persist?

**Not detectably, once the register's own coverage is held constant.**

`politics.persistence_panel()` builds firm-wave observations for 1932–1947 —
1950 has no successor volume — with `reappears`, whether the firm is recorded
again in the next wave. `persistence_models()` fits logistic models with
firm-clustered errors, adding one control at a time.

| Controls | Odds ratio | 95% CI | p |
|---|---|---|---|
| None | 1.84 | 1.48–2.28 | <0.001 |
| Wave | 1.80 | 1.45–2.25 | <0.001 |
| Wave, directors recorded | 1.07 | 0.84–1.37 | 0.59 |
| Wave, directors recorded, their seat counts | 1.03 | 0.80–1.33 | 0.83 |

The raw gap is large and it is compositional. Firms with a connected director
are recorded through 2.5–2.9 directors against 1.6–1.8 for the rest, and how
many directors a firm is recorded through is by far the strongest predictor of
being recorded again: 30% of one-director firm-waves reappear against 89% of
those with four or more. Connected firms are on the right side of that
gradient, and that is most of what the raw comparison picks up.

`persistence_stratified()` drops the functional form and compares firms only
with firms in the same wave recorded through the same number of directors,
pooling the 18 usable cells with inverse-variance weights. The null permutes
the connection flag *within* each cell, so it holds that composition exactly
fixed. The pooled difference is **+0.4 percentage points, permutation
p = 0.88**, against a null interval of −4.1 to +4.3 points. Substituting
national office only (−0.2 pts, p = 0.91) or two or more connected directors
(+1.2 pts, p = 0.65) does not change the picture.

### Survival analysis

The comparison above is one step ahead. A survival analysis uses the whole
spell, and gives the baseline the one-step model hides.

Firms are observed at five unequally spaced points, not continuously, so the
data are interval-censored: a Cox model would misstate what is known. The
model is **discrete-time on the firm-wave risk set, complementary log-log with
log(interval) as an offset** — the specification whose coefficients are
proportional hazards on the underlying continuous time, and whose offset makes
the 6-, 4-, 5- and 3-year gaps comparable. Errors clustered on the firm.
`politics.survival_panel()` builds the risk set; `survival_models()` fits it.

2,228 firm-waves at risk, 1,111 exits, 1,545 firms.

| Controls | HR | 95% CI | p |
|---|---|---|---|
| Wave, tenure | 0.69 | 0.58–0.81 | <0.001 |
| + directors recorded | 0.93 | 0.78–1.11 | 0.41 |
| + their seat counts | 0.93 | 0.77–1.11 | 0.40 |

Same answer as the one-step model, and now with a baseline worth reading in
its own right. **The hazard of leaving the register falls steeply with
tenure**: 63% of firms recorded once are not recorded in the next volume,
27% of those recorded twice, 14% of those recorded three times, 10% of those
recorded four. Adjusted for the interval, the wave hazards are 8.4% a year
across 1932–38, then 18.7%, 16.0% and 14.9%; 1932's is low because its roster
is a selection of prominent firms.

Proportional hazards holds for the term of interest: the association does not
vary with tenure (joint Wald p = 0.29) or with the wave (p = 0.80), so a
single ratio summarises it fairly.

`survival_sensitivity()` re-runs the fullest specification under each
alternative coding:

| Variant | HR | 95% CI | p |
|---|---|---|---|
| First disappearance (primary) | 0.93 | 0.77–1.11 | 0.40 |
| Permanent exit (spell ends at last presence) | 1.00 | 0.83–1.21 | 0.98 |
| National office only | 0.95 | 0.78–1.16 | 0.62 |
| Excluding the 1932 entry cohort | 0.88 | 0.72–1.07 | 0.21 |

Four design facts bound all of it, and none of them is fixable from these
volumes:

* **The event is leaving the register, not failing.** A firm drops out when
  the next volume does not record it — wound up, or merely unlisted.
* **Entry is left-truncated.** The volumes give no founding date, so the clock
  runs from first appearance. `tenure` is volumes observed, never firm age,
  and the steep early hazard is partly the register finding its feet around a
  firm rather than the firm being young.
* **Disappearance is not absorbing.** 5.4% of firms reappear after a missing
  wave. The primary coding treats that as an exit; the permanent-exit variant
  above does not, and moves the estimate to exactly 1.00.
* **Wave, tenure and entry cohort are collinear.** Given wave and tenure the
  cohort is determined, so it is absorbed rather than estimated.

### How to read that

* **This is not evidence that no association exists.** The interval on the
  fullest model still admits odds about a third higher or a fifth lower. With
  508 connected firm-waves, a small association would not be visible here.
* **The outcome is presence in the register, not survival of the firm.** A
  company can trade on for years without a director listed in the annuaire.
  Nothing here speaks to bankruptcy, liquidation or acquisition.
* **The direction is not established either way.** Political connection is
  measured in the same volume as the firm, so nothing separates a firm
  recruiting a connected director from a connected director joining a firm
  already doing well. Even had the association survived, the arrow would not
  follow from these data.
* **The controls are not innocent.** Number of directors recorded is
  downstream of the same editorial choice that records the office, so it is a
  collider risk as much as a confounder. It is used because leaving it out
  guarantees an artefact; that does not make conditioning on it clean.

## Military officers

Rank is coded **separately from civil office**, in `military_officers.csv`.
Folding it into `political` would silently change every rate above, and a
commission is a different kind of tie to the state from a portfolio.

`politics.find_military` codes three tiers — general officer (*ferik*, *lewa*,
major-general, brigadier, admiral), field officer (*miralai*, *kaimakam*,
*bimbachi*, colonel, lieutenant-colonel) and junior officer (captain,
lieutenant) — plus `service_no_rank` for service named without one.

### What has to be excluded, and why

`Général` in this source is almost never a general. It is *Directeur
Général*, *Consul Général*, *Secrétaire Général*, *Assemblée Générale*, or
half of a firm's name. Matching it naively yields 297 hits, of which four are
military. `MILITARY_EXCLUSIONS` therefore blocks the whole family, together
with *Commandeur* (a grade of an order, not a command) and a harbour captain.
*Sirdar* — commander-in-chief of the Egyptian Army — is not in the vocabulary
at all: its one occurrence is "Grand Cordon Sirdar Ali d'Afghanistan", the
Afghan Order of Sardar-i-Ala.

Two further guards handle the entry splitter. Politi prints a rank as an
apposition on the name, before the directorships, so `entry_head` cuts the
entry at whichever comes first — the point where a following entry begins, or
the first role word — and `find_military` additionally discards any rank that
appears after a firm-name marker. Without them, Marryat's *Lt. Col.* attaches
to Mariotti, and Spinks Pacha's *Major General* to whoever the splitter has
merged him with. Six of the 28 raw matches are bleeds of this kind.

### What the coding finds

**22 person-wave records, 19 distinct men; 19 of the 22 hold a board seat.**
The other three sit on a *conseil de surveillance*, which is not a board and
so is not in the network.

Officers sit at the **middle** of their wave: the 51st percentile of board
seats, the 52nd of co-directors, the 56th of brokerage. Against a null that
redraws the same number of officers inside each wave, every difference falls
inside the null interval (permutation p 0.21 to 0.88).

**That is too few to tell, not a demonstration of no difference.** With
nineteen officers the null interval is roughly ±10 percentile points wide, so
anything smaller is invisible here.

One split is worth recording, with the same caution. The five men holding
Ottoman-Egyptian rank — *lewa*, *miralai* — hold exactly one board seat each
and sit at the 41st percentile of brokerage. The fourteen holding British or
European commissions average 2.1 seats and the 61st percentile. Several of the
latter are businessmen with wartime or honorary commissions rather than career
soldiers — Ralph Harari, a Cairo banker, is the most central director in the
whole officer group — which is a caution against reading the group as an
officer corps at all.

Eleven of the 22 records are in 1950 alone. Read that as the annuaire printing
more, as much as anything else: it is the same floor caveat as the civil
offices.

## Wording

The office variables support **associations, not directions**. Office and
directorship are printed in the same entry, so the two are simultaneous in
this data: nothing separates a man reaching boards through political standing
from one whose standing followed his boards, and both are consistent with a
third thing — family, capital, a name — producing each. State what covaries
with what, in which wave, and stop there. In particular:

* Write "office holders are recorded on more boards", not "office brought
  board seats" or "boards brought office".
* Write "is concentrated among", not "was the route into".
* A control that removes an association shows that the association was not
  independent of the control, not that the control is the mechanism.
* A null result of the kind reported above is a failure to detect, bounded by
  the interval, not a demonstration of absence.

Nothing in this dataset identifies an effect of holding office on corporate
position, or of corporate position on holding office.
