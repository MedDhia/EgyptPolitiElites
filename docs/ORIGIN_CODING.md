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

Of 3,373 person-wave observations: 25% Arab/Egyptian, 17% European, 31% local
minority, **27% unknown**. Models are fitted on the 73% classified.

Two things follow. The unknowns are not missing at random — they are the
rarer, more OCR-damaged names, which skew toward the periphery of the network.
And the European category is the smallest, so wave-level European estimates
are the least precise in the study: 1932 rests on 41 Europeans against 22
Arab/Egyptians.

## Non-persons

39 records were dropped as not people at all: decorations (`Grand Officier
Couronne Belge`), offices (`Ancien Ministre`), places (`Le Caire`) and
industries (`Linen Industry`) that the roster prints beside names and the
parser occasionally captured as entries. See `origin.is_person`.

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
