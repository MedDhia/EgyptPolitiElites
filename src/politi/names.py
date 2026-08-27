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


# --- OCR-tolerant matching ----------------------------------------------------
"""
Matching names across a 1930s scan means matching through the scanner's own
confusions. In this corpus the same firm is printed as "Kafr El Zayat Cotton
Co", "Kafr el Zayat Collan Co" and "Kafr El Zay at CoLLan Co", while "Kafr El
Zayat Land Co" is a *different* company. Plain fuzzy matching cannot have both:
loose enough to join Collan to Cotton, it also joins Land to Cotton.

The skeleton solves this by folding characters into the classes the scanner
actually confuses, and nothing else. Under it, Collan and Cotton become the
same string, while Land stays distinct — because l/t and a/o are confusable
but l/c and n/t are not.
"""

# Confusion classes observed in these volumes. The single largest is l <-> t
# ("Administralion", "Egyplian", "Collan"), then c/e ("Banquf'", "Pé·Lrolcs"),
# then a/o and n/u.
_SKELETON_CLASSES = {
    "i": "iltj1|!¡íìîïĺ",     # vertical strokes
    "c": "ceoa0œéèêëàâäôöòó",  # open round forms
    "n": "numh",              # arch forms; rn is read as m and m as n
    "s": "s58$§",
    "b": "bk",
    "g": "g9q",
    "v": "vwy",
    "r": "r",
    "d": "d",
    "p": "p",
    "z": "z",
    "x": "x",
    "f": "f",                  # remapped below; kept explicit for clarity
}
_SKELETON_MAP: dict[str, str] = {}
for _rep, _members in _SKELETON_CLASSES.items():
    for _ch in _members:
        _SKELETON_MAP[_ch] = _rep
_SKELETON_MAP["f"] = "i"       # 'Kal\'r' for 'Kafr': f reads as l

# Words that carry no distinguishing information for a firm.
_COMPANY_STOPWORDS = {
    "co", "cy", "cie", "ltd", "limited", "sae", "sa", "ste", "the", "of",
    "and", "et", "de", "du", "des", "la", "le", "les", "l", "d", "en", "pour",
    "company", "societe", "société", "compagnie", "egypt", "egypte",
}


def ocr_skeleton(name: str) -> str:
    """Fold a company name into its OCR confusion classes.

    Spaces are dropped as well, since the scanner inserts them inside words
    ("Kafr El Zay at"), so the skeleton is a single run of class letters.
    """
    base = normalize_company(name)
    tokens = [t for t in base.split() if t not in _COMPANY_STOPWORDS]
    flat = "".join(tokens) if tokens else base.replace(" ", "")
    return "".join(_SKELETON_MAP.get(ch, ch) for ch in flat)


def skeleton_word(word: str) -> str:
    """Fold a single word into OCR confusion classes, punctuation removed."""
    w = re.sub(r"[^A-Za-zÀ-ÿ]", "", unidecode(word).lower() if word.isascii()
               else word.lower())
    w = unidecode(w).lower()
    return "".join(_SKELETON_MAP.get(ch, ch) for ch in w)


# Structural vocabulary. These words carry the entry's grammar — they mark
# where a role ends and an organisation begins — so OCR damage to them costs
# far more than damage to an ordinary word. Repairing them lets
# "Aaministration", "Adrmnistration" and "ACministrateur" be read as what they
# plainly are.
#
# Deliberately limited to grammar. Words belonging to company names are left
# exactly as printed, so that `company_printed` stays a faithful transcription
# and provenance survives; matching those is the skeleton's job, not this
# function's.
STRUCTURAL_WORDS = [
    "administration", "administrateur", "administrateurs", "conseil",
    "conseils", "membre", "membres", "president", "presidents",
    "vice-president", "directeur", "delegue", "commissaire", "commissaires",
    "secretaire", "comite", "gerant", "censeur", "liquidateur", "conseiller",
]
_STRUCTURAL_SKELETONS = [(skeleton_word(w), w) for w in STRUCTURAL_WORDS]


def repair_structural_words(text: str, threshold: int = 85,
                            max_len_delta: int = 2) -> str:
    """Restore structural words the scanner mangled.

    Matching is fuzzy over skeletons rather than exact, because the common
    digraph confusions (rn/m, cl/d) shift letters rather than substitute them
    and so survive class folding. A token is replaced only when it is long
    enough to be distinctive, close in length to the candidate, and scores
    above *threshold*; capitalisation is preserved.
    """
    from rapidfuzz import fuzz

    def fix(m: re.Match[str]) -> str:
        token = m.group(0)
        if len(token) < 6:
            return token
        sk = skeleton_word(token)
        if not sk:
            return token
        best, best_score = None, 0.0
        for cand_sk, word in _STRUCTURAL_SKELETONS:
            if abs(len(word) - len(token)) > max_len_delta:
                continue
            score = fuzz.ratio(sk, cand_sk)
            if score > best_score:
                best, best_score = word, score
        if best is None or best_score < threshold:
            return token
        if token.isupper():
            return best.upper()
        if token[:1].isupper():
            return best.capitalize()
        return best

    # Letters only: "d'Administration" must be seen as "d" + "Administration",
    # or the whole token is replaced and the elided article is lost.
    return re.sub(r"[A-Za-zÀ-ÿ]+", fix, text)


def company_tokens(name: str) -> list[str]:
    """Meaningful tokens of a company name, legal forms and stopwords removed.

    Single characters are dropped. They are never words here: they are what is
    left of an abbreviation once punctuation goes ("S.A.E" leaves "s" and "e")
    or scanner debris ("1\\afr" leaves "1"), and either way they make two
    printings of one firm look different.
    """
    base = normalize_company(name)
    return [t for t in base.split()
            if len(t) > 1 and t not in _COMPANY_STOPWORDS]


def company_letters(name: str) -> str:
    """A company's meaningful letters, spaces removed, accents folded.

    Spaces go because the scanner inserts them inside words ("Kafr El Zay at");
    the letters stay because they carry the distinction between one firm and
    another, which the skeleton deliberately discards.
    """
    return "".join(company_tokens(name))


# Character pairs this scanner actually confuses. A substitution drawn from
# this set is cheap; any other substitution costs full price. This is what
# separates "Collan"/"Cotton" (three cheap substitutions) from "Land"/"Cotton"
# (a different word).
_CONFUSABLE_PAIRS = {
    "il", "it", "lt", "l1", "i1", "ij", "jl", "if", "fl", "ft", "ti", "li",
    "ce", "co", "eo", "ea", "ao", "ec", "oa",
    "nu", "nm", "mu", "hn", "hb",
    "sf", "s5", "s8", "b6", "bh", "g9", "gq", "qg",
    "vy", "vw", "wv", "uv", "yv",
    "rn", "nr", "cd", "dc", "pd", "db",
    "e1", "el", "0o", "0c", "1l", "5s", "8b",
}
_CONFUSABLE = {frozenset(p) for p in _CONFUSABLE_PAIRS}
_CHEAP = 0.3


def _sub_cost(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return _CHEAP if frozenset((a, b)) in _CONFUSABLE else 1.0


def ocr_distance(a: str, b: str) -> float:
    """Normalised edit distance that forgives the scanner's own mistakes.

    A Levenshtein distance in which substituting one character for another it
    is commonly misread as costs a fraction of an arbitrary substitution. The
    result is divided by the longer length, so 0 is identical and 1 unrelated.

    Unlike a plain ratio, this separates the two cases that matter here: the
    same firm scanned twice differs by many *cheap* substitutions, while two
    different firms differ by few *expensive* ones.
    """
    if a == b:
        return 0.0
    if not a or not b:
        return 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [float(i)]
        for j, cb in enumerate(b, start=1):
            cur.append(min(prev[j] + 1.0,
                           cur[j - 1] + 1.0,
                           prev[j - 1] + _sub_cost(ca, cb)))
        prev = cur
    return prev[-1] / max(len(a), len(b))


def unmatched_content_token(a: str, b: str, tol: float = 0.50,
                            min_len: int = 4) -> bool:
    """Does either name carry a substantial word the other simply lacks?

    A scanner mangles words; it does not invent them. So "Alexandria Insurance"
    and "Alexandria Life Insurance" differ by a *word*, which makes them
    different firms, however small the edit distance between the two strings
    happens to be. "Collan" against "Cotton" is the opposite case: every word
    has a counterpart, just a damaged one.

    Only tokens of at least *min_len* count, since short fragments are as
    likely to be scanning debris as real words. *tol* is deliberately loose:
    this is a veto on top of the whole-name distance, not the main criterion,
    and a badly mangled word must still count as matched. On this corpus the
    worst genuine pair scores 0.41 ("generale" against a truncated "genei")
    while an extra word scores 0.73 ("life").
    """
    ta = [t for t in company_tokens(a) if len(t) >= min_len]
    tb = [t for t in company_tokens(b) if len(t) >= min_len]
    if not ta or not tb:
        return False
    for src, dst in ((ta, tb), (tb, ta)):
        for token in src:
            if min(ocr_distance(token, other) for other in dst) > tol:
                return True
    return False
