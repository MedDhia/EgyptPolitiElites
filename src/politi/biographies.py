"""Parse the annuaire's biographical roster of directors.

Politi closes each volume with *Les Administrateurs des Sociétés Égyptiennes
par actions* — an alphabetical roster in which each entry is one person
followed by their positions across firms::

    Cattaui René Bey, Directeur Général de la S. A. du Wadi Kom Ombo;
    Administrateur de la Commercial Bank of Egypt; Membre du
    Conseil Consultatif de l'Agriculture.

This is a person-side affiliation list, and it is the cleaner of the volume's
two routes into a network: entries are already one-per-person, so the roster
itself does much of the entity resolution that the company section leaves to
inference.

Three properties of the scanned text drive the implementation:

* **No indentation survives** extraction, so entries are segmented by shape —
  a personal name followed by a comma — not by layout.
* **Words break across lines without hyphens** ("de la Na / tional Insurance"),
  so line joining has to decide per break whether to insert a space.
* **OCR corrupts leading capitals** (``~Jembre``, ``:VIembre``, ``Memebre``
  for *Membre*), so role patterns match on stems rather than whole words.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .names import repair_structural_words

# --- page furniture ----------------------------------------------------------

def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def is_running_head(line: str) -> bool:
    """Recognise the page header, which OCR mangles differently every page."""
    f = re.sub(r"[^a-z ]", "", _fold(line))
    if not f.strip():
        return False
    # 'ANNUAIRE DES SOCIÉTÉS ÉGYPTIENNES PAR ACTIONS' plus a folio number.
    hits = sum(tok in f for tok in ("nuaire", "socie", "gyptiennes", "actio"))
    return hits >= 2 and len(line) < 90


# Function words that must keep a space before them when a line is joined.
_FUNCTION_WORDS = {
    "de", "du", "des", "la", "le", "les", "et", "en", "au", "aux", "a", "à",
    "pour", "par", "sur", "ou", "ce", "ces", "son", "ses", "dans", "avec",
    "chez", "comme", "sous", "vers", "entre", "que", "qui", "dont", "ainsi",
    "of", "the", "and", "in", "for", "to",
    # Elided forms, left bare once the apostrophe is split off.
    "d", "l", "qu", "n", "s", "c", "j", "m", "t",
}


def _is_entry_start(line: str) -> bool:
    m = _ENTRY_RE.match(line)
    return bool(m) and _looks_like_person(m.group("name"))


def join_lines(text: str) -> str:
    """Join wrapped lines into one line per roster entry.

    Two decisions per line. First, does it begin a new entry? A personal name
    followed by a comma starts one; anything else continues the entry above.
    Second, when continuing, does a space belong at the join? A break inside a
    word ("Adminis / tration") is joined tight, while a break between words
    ("Membre du / Conseil") keeps its space — the next line's first token
    decides, since a function word means a real word boundary and anything
    else is treated as the tail of a split word.
    """
    out: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or is_running_head(line):
            continue
        if re.fullmatch(r"[A-ZÀ-Þ]", line):   # alphabet divider (A, B, …)
            continue
        if re.fullmatch(r"[\d\W_]+", line):   # stray folio numbers, rules
            continue
        if not out or _is_entry_start(line):
            out.append(line)
            continue
        # Split on the apostrophe too: "d'Administration" must be seen as the
        # function word "d", or the join produces "Conseild'Administration"
        # and the role pattern then swallows the "d".
        first = re.split(r"[\s,;.'’]+", line, maxsplit=1)[0]
        prev = out[-1]
        starts_word = (
            _fold(first).strip("'’") in _FUNCTION_WORDS
            or first[:1].isupper()
            or first[:1].isdigit()
            or not prev[-1:].isalpha()
        )
        out[-1] = prev + (" " if starts_word else "") + line
    return "\n".join(out)


# --- OCR repair ---------------------------------------------------------------

# Words the scanner routinely breaks with a stray space ("Ban que de Crédit").
_SPLIT_PRONE = [
    "banque", "société", "societe", "sociétés", "compagnie", "conseil",
    "administration", "administrateur", "administrateurs", "égyptienne",
    "egyptienne", "égyptiennes", "egypte", "insurance", "company", "national",
    "nationale", "générale", "generale", "immobilière", "foncière", "crédit",
    "assurance", "assurances", "industrielle", "commerciale", "agricole",
    "membre", "président", "directeur", "délégué", "sucreries", "hypothécaire",
    "hotels", "hôtels", "warehouses", "transport", "produce", "trading",
]


def _split_variants(word: str) -> str:
    """Regex matching *word* with at most one stray internal space."""
    alts = [re.escape(word)]
    for i in range(2, len(word) - 1):
        alts.append(re.escape(word[:i]) + r"\s" + re.escape(word[i:]))
    return "(?:" + "|".join(alts) + ")"


_REPAIRS = [
    (re.compile(_split_variants(w), re.I), w) for w in _SPLIT_PRONE
]
# 'de Ia Banque' / 'de 1a Société': the scanner reads l as I or 1.
_ARTICLE_FIX = re.compile(r"\b(de|du|des)\s+[I1l\]|]([ae])\b", re.I)
_APOSTROPHE_FIX = re.compile(r"\b[I1]([''’])")


def repair_ocr_spacing(text: str) -> str:
    """Undo the two OCR damage patterns that corrupt organisation names."""
    text = _ARTICLE_FIX.sub(lambda m: f"{m.group(1)} l{m.group(2)}", text)
    text = _APOSTROPHE_FIX.sub(r"l\1", text)
    for rx, word in _REPAIRS:
        text = rx.sub(lambda m, w=word: _match_case(m.group(0), w), text)
    return text


def _match_case(found: str, canonical: str) -> str:
    return canonical.capitalize() if found[:1].isupper() else canonical


# --- entry segmentation ------------------------------------------------------

HONORIFICS = r"(?:S\.\s?E\.|S\.\s?A\.|LL\.\s?EE\.|Sir|Lord|Dr\.?|M\.|Mme|Mlle|Cav\.|Comm\.)"
_PARTICLES = {"de", "du", "des", "la", "le", "el", "al", "van", "von", "di",
              "da", "bin", "ben", "abou", "abu", "d", "l"}

_ENTRY_RE = re.compile(
    r"^(?P<hon>" + HONORIFICS + r"\s+)?(?P<name>[A-ZÀ-Þ][^,;]{1,45}?),\s+(?=\S)"
)


# A continuation line often opens with a company-name fragment followed by a
# comma, which is shaped exactly like an entry start. Left unchecked it both
# invents a person and truncates the entry it interrupted, so the fragment is
# rejected and the line rejoins the entry above.
_COMPANY_MARKER = re.compile(
    r"(?i)(?:^|\s)(?:c[oy]|ltd|limited|works|usines|s\.?a\.?e|soci[eé]t[eé]|"
    r"compagnie|banque|bank|company|industries|insurance|assurance|trading|"
    r"navigation|hotels?|mining|filature|textiles?|petroleum|theatres?|"
    r"pressing|propri[eé]taire|land)(?:\s|\.|,|$)|&")


def _looks_like_person(name: str) -> bool:
    """Reject company names that happen to carry an internal comma."""
    if _COMPANY_MARKER.search(name):
        return False
    tokens = [t for t in re.split(r"[\s.]+", name.strip()) if t]
    if not (1 <= len(tokens) <= 6):
        return False
    if not any(len(t) >= 3 for t in tokens):
        return False
    for tok in tokens:
        if tok[:1].isupper() or not tok[:1].isalpha():
            continue
        if _fold(tok).strip("'’") in _PARTICLES:
            continue
        return False  # a lowercase word that is not a particle => not a name
    return True


def split_entries(joined: str) -> list[str]:
    """Split the joined roster into one string per person."""
    return [line for line in joined.split("\n") if _is_entry_start(line)]


# --- roles -------------------------------------------------------------------
# Stems, not whole words: OCR eats the leading capital far too often.
ROLE_RULES: list[tuple[str, str]] = [
    # Abbreviated forms. The 1947 volume sets the roster in a compressed style
    # ("Adm. Sté. Al Chark"), so these must be tried before the spelled-out
    # patterns or those entries yield no positions at all.
    (r"\bAdm\.?[- ]?D[ée]l[ée]gu[ée]?\b\.?", "managing_director"),
    (r"\bVice[- ]?Pr[ée]s\.", "vice_president"),
    (r"\bPr[ée]s\.\s*d[ue]\s*[Cc]ons\w*\.?", "president"),
    (r"\bPr[ée]s\.", "president"),
    (r"\bAdm\.", "director"),
    (r"\bDir\.\s*G[ée]n\w*\.?", "general_manager"),
    (r"\bDir\.", "manager"),
    (r"\bMemb\.", "member"),
    (r"\bCens\.", "auditor"),
    (r"[Pp]r[eé]sident\w*\s+d[ue]\s+[Cc]ons\w*(?:\s+d\W*[Aa]dmi\w*)?", "president"),
    (r"[Vv]ice[- ]?[Pp]r[eé]sident", "vice_president"),
    (r"[Pp]r[eé]sident", "president"),
    (r"\w*dministrateur[- ]?D[eé]l[eé]gu\w*", "managing_director"),
    # Must name the second office explicitly: a bare "[- ]?[GgDd]…" also
    # matches the "de" in "Administrateur de la S.A.", which would relabel
    # every ordinary directorship as a managing directorship.
    (r"\w*dministrateur[- ]?(?:[Gg][ée]rant|[Dd]irecteur|[Dd][ée]l[ée]gu[ée]?)\w*",
     "managing_director"),
    (r"\w*dministrateur", "director"),
    (r"\w*embre\w*\s+d[ue]\s+[Cc]ons\w*\s+d\W*[Aa]dmi\w*", "director"),
    (r"\w*embre\w*\s+d[ue]\s+[Cc]omit\w*", "committee_member"),
    (r"\w*embre\w*\s+d[ue]\s+[Cc]ons\w*", "council_member"),
    (r"\w*embre", "member"),
    (r"[Dd]irecteur\w*\s+[GgÉé]\w*", "general_manager"),
    (r"[Dd]irecteur\s+[Ll]ocal", "manager"),
    (r"\w*irecteur", "manager"),
    (r"[Cc]ommissaire\w*", "auditor"),
    (r"[Cc]enseur\w*", "auditor"),
    (r"[Cc]onseiller\w*", "adviser"),
    (r"[Ll]iquidateur\w*", "liquidator"),
    (r"[Aa]ssoci[eé]\w*", "partner"),
    (r"[Dd][eé]l[eé]gu[eé]\w*", "delegate"),
    (r"[Gg][eé]rant\w*", "manager"),
]
_ROLE_RE = re.compile("|".join(f"(?P<r{i}>{p})" for i, (p, _) in enumerate(ROLE_RULES)))
_ROLE_BY_GROUP = {f"r{i}": role for i, (_, role) in enumerate(ROLE_RULES)}

# Organisations that are not joint-stock companies.
_NOT_A_FIRM = re.compile(
    r"(?i)\b(commission|comit[eé]|conseil|chambre|syndicat|universit|facult|"
    r"administration\s+d[eu]s|contributions|douanes|domaines\s+de\s+l|"
    r"minist|gouvernement|acad[eé]mie|ordre|club|association|institut|"
    r"tribunal|cour\b|municipalit)")
_FIRM_HINT = re.compile(
    r"(?i)(soci[eé]t|st[eé]\.|compagnie|banque|bank|company|c[oy]\b|ltd|limited|s\.\s?a\b|"
    r"cie\b|corporation|assurance|insurance|filature|sucrer|cr[eé]dit|"
    r"land\b|hotels?\b|mining|railway|tramway|press|industr)")

# Sits between a role and the organisation it governs: "Président *du Conseil
# d'Administration* de X", "Président *Fondateur* de X".
_CONNECTOR = re.compile(
    r"(?i)^\s*(?:et\s+)?(?:[cdl]{1,2}\W*administration|['’]\s*admini\w*|"
    r"suppl[eé]ants?|adjoints?|"
    r"(?:du|des|[ec]lu|cle)\s+conseils?\w*"
    r"(?:\s+d\W*admi\w*)?|de\s+la\s+direction|"
    r"fondateur|honoraire|sortant|actuel|g[eé]n[eé]ral|local)\b[\s,]*")

_LEAD_PREP = re.compile(r"^\W*(?:de\s+l['’]|de\s+la\s+|de\s+les\s+|des\s+|du\s+|de\s+|d['’]|l['’])\s*",
                        re.I)


@dataclass
class Position:
    role: str
    organisation: str
    is_firm: bool


@dataclass
class Biography:
    printed: str                 # the entry exactly as read
    name: str                    # the name proper
    honorific: str | None
    body: str = ""               # everything after the name, as read
    positions: list[Position] = field(default_factory=list)
    page: int | None = None


def _clean_org(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" .,;:")
    s = _LEAD_PREP.sub("", s)
    # The scanner sometimes renders "la"/"le" with lookalike glyphs, so the
    # preposition strips but its article does not. Remove a stranded one.
    s = re.sub(r"(?i)^(?:l[ae]|les|du|des)[\s.\-]+(?=[A-Z0-9])", "", s)
    # Drop a trailing place, which Politi appends to some firms.
    s = re.sub(r",\s*(?:Le Caire|Alexandrie|Cairo|Alexandria|Port[- ]Sa[iï]d)\s*$",
               "", s, flags=re.I)
    return s.strip(" .,;:")


# Roles that, by themselves, describe membership of a public or professional
# body rather than a company board.
_BODY_ROLES = {"council_member", "committee_member", "member", "adviser"}


def _classify(org: str, role: str = "") -> bool:
    """Is this organisation a joint-stock company rather than a public body?"""
    if _FIRM_HINT.search(org):
        return True
    if _NOT_A_FIRM.search(org):
        return False
    if role in _BODY_ROLES:
        return False  # 'Membre du Conseil …' with no company marker
    return bool(re.search(r"[A-Z]", org))


_NAME_TITLE_WORDS = {"me", "dr", "rt", "hon", "sir", "bart", "mp", "cav", "uff",
                     "comm", "mme", "mlle", "st", "ste", "van", "von", "de", "di",
                     "el", "al", "abou", "abu", "ben", "bin", "la", "le"}


def _looks_like_given_names(seg: str) -> bool:
    """Is this segment a given-name run rather than the start of the body?

    Volumes differ: 1932 and 1947 print "Cattaui René Bey, <positions>", while
    1938, 1942 and 1950 invert to "Adda, Achille, <positions>". Without this
    test the inverted volumes yield a bare surname, and every person sharing a
    surname collapses into one node.
    """
    seg = seg.strip()
    if not (2 <= len(seg) <= 40):
        return False
    if _ROLE_RE.search(seg):
        return False
    bare = re.sub(r"\([^)]*\)", " ", seg)          # drop "(Bey)", "(Baron)"
    tokens = [t for t in re.split(r"[\s.;,]+", bare) if t]
    if not tokens:
        return False
    for tok in tokens:
        if tok[:1].isupper() or not tok[:1].isalpha():
            continue
        if _fold(tok).strip("'’") in _NAME_TITLE_WORDS:
            continue
        return False
    return True


# Offices, decorations and qualifications that the roster prints hard against
# a name — "Sade.k, Wahba (Pacha),Sénateur", "Abdel Haï Khalil Bey Député" —
# and that the name/body split therefore swallows. None of them is part of a
# name. They are stripped here and recovered as data in `politics.py`: a seat
# in parliament or a portfolio is a variable, not a spelling.
_NAME_TAIL = re.compile(
    r"(?i)\s+(?:anc(?:ien|\.)\b|(?:anc(?:ien|\.)\s+)?(?:"
    r"d[eé]put[eé]|s[eé]nateur|ministre|magistrat|gouverneur|ambassadeur|"
    r"consul(?:\s+g[eé]n[eé]ral)?|chambellan|sous[\s-]secr[eé]taire|"
    r"conseiller|commandeur|officier|chevalier|grand[\s-]croix|croix\s+de\s+guerre"
    r")\b).*$")

# The space after the comma is optional: the scanner drops it often enough
# — "Wahba (Pacha),Sénateur" — that requiring it costs the given name.
_INVERTED_RE = re.compile(r"([^,;]{2,40}),\s*(?=[A-ZÀ-Þ])")


def _split_name_and_body(entry: str) -> tuple[str | None, str, str] | None:
    """Return (honorific, full name, body) for one roster entry."""
    m = _ENTRY_RE.match(entry)
    if not m:
        return None
    hon = (m.group("hon") or "").strip() or None
    name = re.sub(r"\s+", " ", m.group("name")).strip()
    rest = entry[m.end():]
    m2 = _INVERTED_RE.match(rest)
    if m2 and _looks_like_given_names(m2.group(1)):
        given = re.sub(r"\s+", " ", m2.group(1)).strip(" .,;")
        name = f"{name} {given}"
        rest = rest[m2.end():]
    name = re.sub(r"[()]", " ", name)   # "(Bey)" -> " Bey ", so rank is read
    # An office or decision printed against the name belongs to the body, not
    # to the name. Never strip the first token: a surname may be Chevalier.
    trimmed = _NAME_TAIL.sub("", name.strip())
    if trimmed.strip(" .,;"):
        name = trimmed
    return hon, re.sub(r"\s+", " ", name).strip(" .,;"), rest


def parse_entry(entry: str, page: int | None = None) -> Biography:
    printed = entry
    entry = repair_ocr_spacing(entry)
    split = _split_name_and_body(entry)
    if split is None:
        return Biography(printed=printed, name="", honorific=None, page=page)
    hon, name, body = split
    # Restore the structural vocabulary the scanner mangled — but only in the
    # body. Personal names are left exactly as printed: they are the one place
    # a French word is not expected, so repairing there turns "Achille" into
    # "Comité". `printed` keeps the whole entry as scanned regardless.
    body = repair_structural_words(body)

    bio = Biography(printed=printed, name=name, honorific=hon, body=body,
                    page=page)
    last_roles: list[str] = []
    for clause in re.split(r"\s*[;:]\s*", body):
        if not clause.strip():
            continue
        matches = list(_ROLE_RE.finditer(clause))
        if matches:
            # "Président du Conseil d'Administration et Administrateur-Délégué
            # de X" names one organisation under two roles, so take every role
            # in the clause and read the organisation after the last of them.
            roles, seen = [], set()
            for rm in matches:
                r = _ROLE_BY_GROUP[rm.lastgroup]
                if r not in seen:
                    seen.add(r)
                    roles.append(r)
            tail = clause[matches[-1].end():]
            last_roles = roles
        elif last_roles and _LEAD_PREP.match(clause):
            # "…de The Alexandria Water Cy; de la Filature Nationale; de …"
            # A bare 'de …' clause continues the previous role.
            roles, tail = last_roles, clause
        else:
            continue

        prev = None
        while tail != prev:                    # strip stacked connectors
            prev = tail
            tail = _CONNECTOR.sub("", tail)

        for part in re.split(r"\s+et\s+(?=d[eu\']|l[\'’]|la\b|des\b)", tail):
            org = _clean_org(part)
            if len(org) < 3 or not re.search(r"[A-Za-zÀ-ÿ]{3}", org):
                continue
            for role in roles:
                bio.positions.append(
                    Position(role=role, organisation=org, is_firm=_classify(org, role)))
    return bio


ROSTER_HEADING = re.compile(
    r"(?i)les\s+administrateurs\s+des\s+soci[eé]t[eé]s|nomenclature")


def _entry_count(body: str) -> int:
    n = 0
    for line in join_lines(body or "").split("\n"):
        if _is_entry_start(line) and parse_entry(line).positions:
            n += 1
    return n


def find_roster_pages(pages: dict[int, str], min_entries: int = 3,
                      lookahead: int = 8) -> tuple[int, int] | None:
    """Locate the roster: from its heading to the last page of entries.

    The heading phrase also appears in the front matter's table of contents, so
    a candidate only counts if pages soon after it actually carry entries. The
    gap between heading and first entry varies between volumes — 1932 runs the
    heading two pages ahead of the entries, 1942 has a second title page in
    between — hence the lookahead rather than a fixed offset.
    """
    ordered = sorted(pages)
    for idx, n in enumerate(ordered):
        if not ROSTER_HEADING.search(pages[n] or ""):
            continue
        follow = ordered[idx + 1: idx + 1 + lookahead]
        start = next((m for m in follow if _entry_count(pages[m]) >= min_entries), None)
        if start is None:
            continue  # a mention in the contents, not the section itself
        end, gap = start, 0
        for m in ordered[ordered.index(start):]:
            if _entry_count(pages[m]) >= min_entries:
                end, gap = m, 0
            else:
                gap += 1
                if gap > 2:   # roster pages can carry a sparse page or two
                    break
        return start, end
    return None


def parse_roster(pages: dict[int, str]) -> list[Biography]:
    """Parse every biographical entry in a volume."""
    span = find_roster_pages(pages)
    if span is None:
        return []
    start, end = span
    bios: list[Biography] = []
    for n in range(start, end + 1):
        joined = join_lines(pages.get(n, "") or "")
        for entry in split_entries(joined):
            bio = parse_entry(entry, page=n)
            if bio.name and bio.positions:
                bios.append(bio)
    return bios
