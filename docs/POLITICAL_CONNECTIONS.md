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
| `office_and_seats.png` | Office holders sat on 2.3–2.4× as many boards (1938 onward) |
| `connected_firms.png` | 15–25% of firms had at least one connected director |
| `office_by_origin.png` | 17.2% of Arab/Egyptian directors held office against 2.3% of Europeans — a 7.5× gap |
| `office_position.png` | Office is associated with more seats, not a more central position per seat: the raw brokerage gap largely closes once seat count is held constant |
| `origin_adjusted.png` | Holding office constant leaves the origin coefficients essentially unchanged, so office is not the channel behind them |

The office variables are **associational**. Directors were recruited to boards
because they were already prominent, and the office is a record of that
prominence, not an instrument for it. Nothing here identifies an effect of
holding office on corporate position.
