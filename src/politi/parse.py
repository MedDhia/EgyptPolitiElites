"""Parse annuaire text into company records and directorship rows.

Politi's entries follow a stable layout across editions::

    SOCIÉTÉ ANONYME DES EAUX DU CAIRE
    Siège social : Le Caire, 10 rue Kasr-el-Nil.
    Constituée le 12 mai 1928. — Durée : 50 ans.
    Capital : L.E. 500.000 divisé en 100.000 actions de L.E. 5.
    Conseil d'Administration :
    Président : S.E. Ismaïl Sidky Pacha
    Administrateurs : MM. Ahmed Abboud Pacha, Élie N. Mosseri, ...

The parser is written to survive OCR damage: accents may be dropped, ``:`` may
be read as ``.``, and role labels may be split across lines. Every regex is
therefore accent-tolerant and matched against a de-accented shadow copy while
offsets are kept against the original text so that quotations stay faithful.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from unidecode import unidecode

from .names import PersonName, normalize_company, parse_person


def fold_accents(s: str) -> str:
    """Strip accents while preserving string length, so that regex offsets
    taken on the folded shadow remain valid indices into the original text."""
    import unicodedata

    out = []
    for ch in s:
        base = unicodedata.normalize("NFD", ch)[0]
        out.append(base if (len(base) == 1 and base.isascii()) else ch)
    return "".join(out)

# --- role vocabulary ---------------------------------------------------------
# Mapped onto a small controlled vocabulary; see docs/CODEBOOK.md.
ROLE_PATTERNS: list[tuple[str, str]] = [
    (r"presidents?\s+d[' ]honneur", "honorary_president"),
    (r"presidents?\s+du\s+conseil", "president"),
    (r"vice[- ]presidents?", "vice_president"),
    (r"presidents?", "president"),
    (r"administrateurs?[- ]delegues?", "managing_director"),
    (r"administrateurs?[- ]gerants?", "managing_director"),
    (r"vice[- ]administrateurs?", "director"),
    (r"administrateurs?", "director"),
    (r"membres?\s+du\s+conseil", "director"),
    (r"conseillers?", "director"),
    (r"directeurs?\s+generaux", "general_manager"),
    (r"directeurs?\s+general", "general_manager"),
    (r"directeurs?", "manager"),
    (r"secretaires?\s+generaux", "secretary"),
    (r"secretaires?", "secretary"),
    (r"commissaires?\s+aux\s+comptes", "auditor"),
    (r"commissaires?", "auditor"),
    (r"censeurs?", "auditor"),
    (r"liquidateurs?", "liquidator"),
]
_ROLE_RE = re.compile(
    r"(?m)^\s*(" + "|".join(p for p, _ in ROLE_PATTERNS) + r")\s*[:.—-]\s*",
    re.IGNORECASE,
)
_ROLE_LOOKUP = [(re.compile(r"^" + p + r"$", re.IGNORECASE), r) for p, r in ROLE_PATTERNS]

BOARD_HEADER_RE = re.compile(
    r"(?im)^\s*conseil\s+d[' ]?administration\s*[:.—-]?\s*$"
)

# A company header: a full line in capitals, at least two "word" characters,
# not a running head and not one of the section labels.
HEADER_RE = re.compile(r"(?m)^[ \t]*([A-Z0-9ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜ&\"'()., \-«»/]{6,120})[ \t]*$")
_NOT_HEADER = re.compile(
    r"^(?:conseil|siege|capital|objet|bilan|actif|passif|exercice|annuaire|sommaire|"
    r"table|index|societes?\s+egyptiennes|page|tome|chapitre|l\.?e\.?|total)\b",
    re.IGNORECASE,
)

FIELD_RES = {
    "seat": re.compile(r"(?i)si[eè]ge\s+social\s*[:.—-]\s*(.+)"),
    "founded": re.compile(r"(?i)constitu[eé]e?\s+le\s+(.+?)(?:[.;]|\s+[-—]|$)"),
    "duration": re.compile(r"(?i)dur[eé]e\s*[:.—-]\s*(.+?)(?:[.;]|$)"),
    "purpose": re.compile(r"(?im)objet\s*[:.—-]\s*([^\n]+?)(?:\s*$)"),
    "capital": re.compile(
        r"(?im)capital(?:\s+social)?\s*[:.—-]\s*([^\n]+?)(?:\s+divis|\s*$)"),
}

CITY_RE = re.compile(
    r"(?i)\b(le\s+caire|cairo|alexandri[ea]|port[- ]sa[iï]d|suez|tanta|mansourah?|"
    r"zagazig|assiout|damanhour|minieh|helouan|heliopolis)\b"
)

_AMOUNT_RE = re.compile(
    r"(?i)(L\.?\s?E\.?|£\s?E|£|Frs?\.?|francs?|\$|P\.?T\.?)\s*([\d][\d .,']*)"
)


@dataclass
class Directorship:
    company: str
    person: PersonName
    role: str
    order: int          # position within the printed list (rank proxy)
    source_page: int | None = None


@dataclass
class Company:
    name: str
    key: str
    seat: str | None = None
    city: str | None = None
    founded: str | None = None
    duration: str | None = None
    purpose: str | None = None
    capital_raw: str | None = None
    capital_currency: str | None = None
    capital_amount: float | None = None
    source_page: int | None = None
    directorships: list[Directorship] = field(default_factory=list)


# --- helpers -----------------------------------------------------------------

def _canonical_role(label: str) -> str:
    lab = unidecode(label).strip().lower()
    for rx, role in _ROLE_LOOKUP:
        if rx.match(lab):
            return role
    return "other"


def parse_capital(raw: str) -> tuple[str | None, float | None]:
    """Parse 'L.E. 500.000' -> ('LE', 500000.0). French thousands separators."""
    m = _AMOUNT_RE.search(raw)
    if not m:
        return None, None
    # Deliberately not unidecode()d: it renders '£' as 'PS'.
    cur = m.group(1).upper().replace(".", "").replace(" ", "")
    cur = {"LE": "LE", "£E": "LE", "E": "LE", "£": "GBP", "FR": "FRF", "FRS": "FRF",
           "FRANC": "FRF", "FRANCS": "FRF", "$": "USD", "PT": "PT"}.get(cur, cur)
    digits = re.sub(r"[ .,']", "", m.group(2))
    if not digits.isdigit():
        return cur, None
    return cur, float(digits)


def split_person_list(chunk: str) -> list[str]:
    """Split a printed roster into individual names.

    Handles the 'MM.' plural marker, comma/semicolon separators, a trailing
    'et', and drops parenthetical glosses such as '(démissionnaire)'.
    """
    s = re.sub(r"\s+", " ", chunk).strip()
    s = re.sub(r"\((?:[^()]*)\)", " ", s)          # drop glosses
    s = re.sub(r"(?i)^\s*MM\.?\s+", "", s)          # plural honorific
    s = re.sub(r"(?i)\bet\b", ",", s)
    s = s.rstrip(" .;,")
    parts = [p.strip(" .;,") for p in re.split(r"[;,]", s)]
    out = []
    for p in parts:
        if not p or len(p) < 3:
            continue
        if not re.search(r"[A-Za-zÀ-ÿ]{2,}", p):
            continue
        out.append(p)
    return out


def _is_header(line: str) -> bool:
    stripped = line.strip()
    if not (6 <= len(stripped) <= 120):
        return False
    if _NOT_HEADER.match(fold_accents(stripped)):
        return False
    letters = [c for c in stripped if c.isalpha()]
    if len(letters) < 4:
        return False
    # Overwhelmingly capitals -> a display header rather than running prose.
    return sum(c.isupper() for c in letters) / len(letters) > 0.85


def iter_company_blocks(text: str) -> list[tuple[str, str]]:
    """Split volume text into (header, body) blocks, one per company entry."""
    lines = text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    for line in lines:
        if _is_header(line):
            blocks.append((re.sub(r"\s+", " ", line.strip(" .")), []))
        elif blocks:
            blocks[-1][1].append(line)
    # Only keep blocks that actually look like company entries.
    out = []
    for header, body in blocks:
        joined = "\n".join(body)
        shadow = fold_accents(joined)
        if BOARD_HEADER_RE.search(shadow) or _ROLE_RE.search(shadow):
            out.append((header, joined))
    return out


def parse_board(body: str) -> list[tuple[str, str]]:
    """Return (role, raw_name) pairs from a company body, in printed order."""
    shadow = fold_accents(body)
    matches = list(_ROLE_RE.finditer(shadow))
    pairs: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        role = _canonical_role(m.group(1))
        chunk = body[m.end():end]
        # A roster ends at the next labelled field (Capital:, Bilan:, ...).
        cut = re.search(
            r"(?im)^\s*(?:capital|bilan|si[eè]ge|objet|exercice|actif|passif)\b",
            fold_accents(chunk))
        if cut:
            chunk = chunk[: cut.start()]
        for name in split_person_list(chunk):
            pairs.append((role, name))
    return pairs


def parse_company_block(header: str, body: str, page: int | None = None) -> Company:
    name = header.strip(" .:-")
    comp = Company(name=name, key=normalize_company(name), source_page=page)

    flat = re.sub(r"\n(?=[a-zà-ÿ])", " ", body)  # rejoin wrapped lines
    flat_shadow = fold_accents(flat)
    for field_name, rx in FIELD_RES.items():
        m = rx.search(flat_shadow)
        if not m:
            continue
        value = flat[m.start(1):m.end(1)]  # original text, accents intact
        setattr(comp, "capital_raw" if field_name == "capital" else field_name,
                re.sub(r"\s+", " ", value).strip(" .;"))
    if comp.seat:
        city = CITY_RE.search(comp.seat)
        comp.city = _canonical_city(city.group(1)) if city else None
    if comp.capital_raw:
        comp.capital_currency, comp.capital_amount = parse_capital(comp.capital_raw)

    for order, (role, raw_name) in enumerate(parse_board(body), start=1):
        comp.directorships.append(
            Directorship(company=name, person=parse_person(raw_name), role=role,
                         order=order, source_page=page)
        )
    return comp


def _canonical_city(s: str) -> str:
    t = unidecode(s).lower().replace("-", " ")
    if t.startswith("le caire") or t == "cairo":
        return "Cairo"
    if t.startswith("alexandri"):
        return "Alexandria"
    if t.startswith("port sa"):
        return "Port Said"
    return s.title()


def parse_volume(text: str) -> list[Company]:
    """Parse a whole volume's text into company records."""
    from .pdftext import page_of, strip_page_marks

    companies: list[Company] = []
    marked = text
    plain = strip_page_marks(text)
    has_marks = marked is not plain and "<<<PAGE" in marked
    for header, body in iter_company_blocks(plain):
        page = None
        if has_marks:
            idx = marked.find(header)
            page = page_of(marked, idx) if idx >= 0 else None
        companies.append(parse_company_block(header, body, page=page))
    return companies
