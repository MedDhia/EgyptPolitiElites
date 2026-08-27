# Coding directors by community of origin

## What the variable is

`origin` places each director in one of four categories, **imputed from the
printed name**. It is a measured variable with error, not an observation.

| Value | Who |
|---|---|
| `arab_egyptian` | Muslim Egyptians, and Copts (Egyptian Christians) |
| `european` | British, French, Belgian, Swiss, Italian, German subjects |
| `local_minority` | The *mutamassirun*: Egyptian and Sephardi Jews, Greeks, Armenians, Syro-Lebanese Christians |
| `unknown` | Not classifiable from the name |

## Why four categories and not two

Interwar Egyptian boards were not split between Europeans and Egyptians. A
third bloc supplied more directors than either — 31% of all person-wave
observations, against 25% Arab/Egyptian and 17% European. Folding them into
"European" would credit their positions to foreign capital; folding them into
"Egyptian" would erase the distinction the period turned on. They are held
separate, and the European/Arab contrast is estimated with them in the model.

## How a name is read

In priority order:

1. **Surname**, by lexicon and orthography (Armenian `-ian`, Greek `-akis`,
   `-poulos`, `-achi`). Surnames carry community here.
2. **Arabic given names and particles** (`Mohamed`, `Abdel`, `Abou`, `El-`),
   which are close to unambiguous and give the Arab category its recall.

Unmatched names stay `unknown` rather than being guessed. Every record keeps
the rule that fired (`origin_rule`), so any coding can be traced and corrected.

### One rule that matters more than it looks

**A European given name is never evidence of European origin.** The minority
bourgeoisie used French given names universally — Joseph Cattaui, Élie
Mosseri, Nicolas Bassili. An early version of this coder had `nicolas` in a
French surname lexicon and duly classified *Bassili Nicolas Alexandre*, a
Copt, as European. Since the whole analysis is a European/Egyptian contrast,
that error pushed directly on the estimand. European classification now
requires a token outside `EUROPEAN_GIVEN`.

## Coverage

Of 3,388 person-wave observations: 23% Arab/Egyptian, 14% European, 25% local
minority, **37% unknown**. Models are fitted on the 63% classified.

Two things follow. The unknowns are not missing at random — they are the
rarer, more OCR-damaged names, which skew toward the periphery of the network.
And the European category is the smallest, so wave-level European estimates
are the least precise in the study: 1932 rests on 42 Europeans against 23
Arab/Egyptians.

## Non-persons

28 records were dropped as not people at all: offices (`Ancien Ministre`),
places (`Le Caire`), firm fragments (`Maison Choremi`) and industries
(`Egyptienne de Tuyaux`) that the roster prints beside names and the parser
occasionally captured as entries.

The test is **where** the honour or office sits, not whether it is present.
An earlier version matched this vocabulary anywhere in the string and so
discarded 66 real directorships — among them `Baehler Charles Commandeur
Medjidié`, one of the best-connected men in the dataset, whose entry simply
carries his decoration after his name. `origin.is_person` now strips leading
articles and rank modifiers and tests only the opening of what remains, with
three position-free rules for markers no printed name in this source carries:
an academic institution (`St. John's College Oxford`), a company suffix
(`Upper Egypt Oinning-Co`), and a degree read beside a university.

## How to check it

```python
from politi.origin import classify_frame
df = classify_frame(persons.label)
df[df.origin == "european"].sample(40)   # read them
```

The lexicons are ordinary Python sets in `src/politi/origin.py`. Correcting a
misclassification means adding the surname to the right set and rebuilding —
there is no model to retrain. If you are going to publish from this variable,
read a few hundred and fix what is wrong; the coding is a starting point, not
an authority.
