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
