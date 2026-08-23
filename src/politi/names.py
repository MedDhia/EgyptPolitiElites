"""Parsing and normalising personal names as they appear in Politi.

Politi prints directors in a French civil register style with Ottoman-Egyptian
rank suffixes, e.g.::

    S.E. Ismaïl Sidky Pacha
    M. Joseph A. Cattaui Bey
    MM. Ahmed Abboud Pacha, Élie N. Mosseri

Two jobs are done here:

1. **Decomposition** — split a printed name into an honorific prefix, a rank
   suffix (Pacha/Bey/Effendi), and the name proper. The rank is *kept*: for
   elite research it is a status attribute, not noise.
2. **Normalisation** — reduce the name proper to a matching key that is stable
   across the French transliteration variants used inconsistently between
   volumes (Cattaui / Cattaoui / Qattawi; Sidky / Sidqi; Abboud / Aboud).

The key is deliberately aggressive: it is a *blocking* key for candidate
generation, not an identity claim. Final linkage is decided in ``resolve.py``
by fuzzy scoring within a block.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from unidecode import unidecode

# --- vocabulary --------------------------------------------------------------

# Honorifics printed before the name. Order matters: longest first.
PREFIXES = [
    "s.a.r.", "s.a.s.", "s.e.", "s.a.", "s.m.",
    "mm.", "mme", "mlle", "m.", "dr.", "dr", "me", "ing.", "prof.",
    "sir", "lord", "lady", "hon.", "rev.",
    "prince", "princesse", "comte", "comtesse", "baron", "baronne",
    "cheikh", "sheikh", "chekh",
    "general", "gen.", "colonel", "col.", "commandant", "capitaine",
]

# Ottoman-Egyptian rank suffixes. These are civil ranks, abolished in 1953.
RANKS = {
    "pacha": "pasha", "pasha": "pasha", "bacha": "pasha",
    "bey": "bey", "beik": "bey", "bek": "bey",
    "effendi": "effendi", "effendy": "effendi",
    "agha": "agha",
}

# Honorific-like prefixes that are part of the *name* and must be preserved
# (nobiliary particles).
PARTICLES = {"de", "di", "da", "del", "della", "van", "von", "el", "al", "abu", "abou", "ibn", "ben"}

_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(re.escape(p) for p in sorted(PREFIXES, key=len, reverse=True)) + r")\s+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PersonName:
    """A decomposed director name."""

    raw: str            # exactly as printed
    display: str        # cleaned name proper, diacritics kept
    rank: str | None    # 'pasha' | 'bey' | 'effendi' | 'agha' | None
    prefix: str | None  # honorific as printed, lowercased ('s.e.', 'm.', ...)
    key: str            # transliteration-invariant blocking key
    surname_key: str    # key of the last name token, for coarse blocking

    @property
    def is_titled(self) -> bool:
        return self.rank is not None


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


# --- normalisation -----------------------------------------------------------

# Ordered rewrite rules. Order is load-bearing: the vowel rules must run before
# consonant folding so that 'aou' collapses to 'au' before doubles are reduced.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"aou"), "au"),
    (re.compile(r"eou"), "eu"),
    (re.compile(r"ou"), "u"),
    (re.compile(r"aw"), "au"),
    (re.compile(r"ow"), "u"),
    (re.compile(r"w"), "u"),
    (re.compile(r"ch"), "sh"),      # French ch -> sh (Chérif / Sherif)
    (re.compile(r"ph"), "f"),
    (re.compile(r"q"), "k"),
    (re.compile(r"c(?=[eiy])"), "s"),
    (re.compile(r"c"), "k"),
    (re.compile(r"y"), "i"),
    # Doubles must collapse *before* the intervocalic-h rule, so that Nahhas
    # reduces to Nahas and only then loses its h, matching Nahas itself.
    (re.compile(r"(.)\1+"), r"\1"),  # collapse doubled letters
    (re.compile(r"(?<=[aeiou])h(?=[aeiou])"), ""),  # silent intervocalic h
    (re.compile(r"j"), "g"),        # Djemal / Gemal
    (re.compile(r"e$"), ""),
]


def normalize_token(token: str) -> str:
    """Reduce one name token to its transliteration-invariant form."""
    t = unidecode(token).lower()
    t = re.sub(r"[^a-z]", "", t)
    if not t:
        return ""
    for pattern, repl in _RULES:
        t = pattern.sub(repl, t)
    # A second pass: the rewrites above can create new doubles (e.g. 'ch'->'sh'
    # next to an existing 's').
    t = re.sub(r"(.)\1+", r"\1", t)
    return t


def normalize_name(name: str) -> str:
    """Blocking key for a whole name: normalised tokens, particles dropped."""
    tokens = [t for t in re.split(r"[\s'\-’.]+", name) if t]
    out: list[str] = []
    for tok in tokens:
        bare = unidecode(tok).lower().strip(".")
        if bare in PARTICLES:
            continue
        if len(bare) <= 1:  # a bare initial carries no matching signal
            continue
        n = normalize_token(tok)
        if n:
            out.append(n)
    return " ".join(out)


def parse_person(raw: str) -> PersonName:
    """Decompose one printed director name."""
    s = re.sub(r"\s+", " ", raw).strip(" ,;.•-")
    prefix = None
    m = _PREFIX_RE.match(s)
    if m:
        prefix = m.group(0).strip().lower()
        s = s[m.end():]

    rank = None
    tokens = s.split()
    while tokens:
        tail = unidecode(tokens[-1]).lower().strip(".,;")
        if tail in RANKS:
            rank = RANKS[tail]
            tokens.pop()
        else:
            break
    display = " ".join(tokens).strip(" ,;")

    key = normalize_name(display)
    surname_key = key.split()[-1] if key else ""
    return PersonName(
        raw=raw.strip(), display=display, rank=rank, prefix=prefix,
        key=key, surname_key=surname_key,
    )


# --- company names -----------------------------------------------------------

_LEGAL_FORMS = [
    "societe anonyme egyptienne", "societe anonyme", "societe egyptienne",
    "compagnie egyptienne", "compagnie", "societe", "s.a.e.", "s.a.",
    "the", "company limited", "company ltd", "co. ltd", "ltd", "limited",
]
_LEGAL_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(f) for f in sorted(_LEGAL_FORMS, key=len, reverse=True)) + r")\b"
)


def normalize_company(name: str) -> str:
    """Blocking key for a company: legal form and stopwords stripped."""
    s = unidecode(name).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _LEGAL_RE.sub(" ", s)
    s = re.sub(r"\b(?:de|des|du|d|la|le|les|l|et|of|and|for|pour|en|a|au|aux)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
