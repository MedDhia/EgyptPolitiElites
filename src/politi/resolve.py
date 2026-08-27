"""Cross-wave entity resolution.

The same director is printed differently between volumes — a rank gained
(``Bey`` in 1938, ``Pacha`` in 1947), an initial dropped, a transliteration
changed. Linking those mentions is what turns five separate directories into a
panel, so the procedure is kept explicit and auditable rather than hidden in a
similarity threshold.

Procedure
---------
1. **Block** on the normalised surname key (``names.normalize_name``), so only
   plausibly-related mentions are ever compared.
2. **Score** each within-block pair with a token-sort ratio over the full
   normalised key.
3. **Gate** on given-name compatibility: two mentions may merge only if their
   given-name initials agree, treating a bare initial as compatible with any
   given name that starts with it. This is what keeps brothers and
   fathers/sons — extremely common in these boards — from collapsing.
4. **Union** the surviving pairs and emit a stable id per cluster.

Every merge is written to ``person_crosswalk.csv`` so the linkage can be
inspected and corrected by hand; ``docs/CODEBOOK.md`` explains the columns.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from rapidfuzz import fuzz

from .names import (PersonName, company_letters, normalize_company,
                    ocr_distance, ocr_skeleton, unmatched_content_token)


@dataclass
class Mention:
    """One printed occurrence of a person in one volume."""

    mention_id: int
    year: int
    company: str
    role: str
    order: int
    person: PersonName
    page: int | None = None


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def _given_tokens(key: str) -> list[str]:
    parts = key.split()
    return parts[:-1] if len(parts) > 1 else []


def given_names_compatible(a: PersonName, b: PersonName) -> bool:
    """Do the given names of two mentions agree, allowing bare initials?

    Initials are recovered from the *printed* name because ``normalize_name``
    drops single characters.
    """
    ia = _initials(a)
    ib = _initials(b)
    if not ia or not ib:
        return True  # one side is surname-only; leave the decision to the score
    return ia[0] == ib[0]


def _initials(p: PersonName) -> list[str]:
    toks = [t for t in re.split(r"[\s.'’-]+", p.display) if t]
    return [t[0].upper() for t in toks[:-1]] if len(toks) > 1 else []


def cluster_persons(
    mentions: list[Mention], threshold: int = 88
) -> tuple[dict[int, str], dict[str, dict]]:
    """Return (mention_id -> person_id) and a per-person summary."""
    blocks: dict[str, list[Mention]] = defaultdict(list)
    for m in mentions:
        if m.person.surname_key:
            blocks[m.person.surname_key].append(m)

    uf = _UnionFind()
    for m in mentions:
        uf.find(m.mention_id)

    for _, group in blocks.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.person.key == b.person.key:
                    uf.union(a.mention_id, b.mention_id)
                    continue
                if not given_names_compatible(a.person, b.person):
                    continue
                ta, tb = set(a.person.key.split()), set(b.person.key.split())
                if ta <= tb or tb <= ta:
                    # One printed form abbreviates the other ("J. Cattaui" vs
                    # "Joseph Cattaui"): the surname block and the initial gate
                    # have already been passed, and the fuzzy score is
                    # unreliable when one key is much shorter.
                    uf.union(a.mention_id, b.mention_id)
                elif fuzz.token_sort_ratio(a.person.key, b.person.key) >= threshold:
                    uf.union(a.mention_id, b.mention_id)

    clusters: dict[int, list[Mention]] = defaultdict(list)
    for m in mentions:
        clusters[uf.find(m.mention_id)].append(m)

    mention_to_person: dict[int, str] = {}
    people: dict[str, dict] = {}
    for n, (root, group) in enumerate(sorted(clusters.items()), start=1):
        pid = f"P{n:05d}"
        # Canonical label: the most frequent printed form, longest breaking ties.
        counts = Counter(m.person.display for m in group)
        label = max(counts, key=lambda d: (counts[d], len(d)))
        ranks = [m.person.rank for m in group if m.person.rank]
        years = sorted({m.year for m in group})
        people[pid] = {
            "person_id": pid,
            "label": label,
            "name_key": group[0].person.key,
            "variants": sorted({m.person.display for m in group}),
            "highest_rank": _highest_rank(ranks),
            "rank_by_year": {m.year: m.person.rank for m in group if m.person.rank},
            "years_present": years,
            "n_mentions": len(group),
        }
        for m in group:
            mention_to_person[m.mention_id] = pid
    return mention_to_person, people


_RANK_ORDER = {"effendi": 1, "agha": 1, "bey": 2, "pasha": 3}


def _highest_rank(ranks: list[str]) -> str | None:
    if not ranks:
        return None
    return max(ranks, key=lambda r: _RANK_ORDER.get(r, 0))


def cluster_companies(
    pairs: list[tuple[int, str]], max_distance: float = 0.20,
    max_diameter: float = 0.30, near_identical: float = 0.10,
    candidate_cutoff: int = 80, min_letters: int = 8
) -> tuple[dict[tuple[int, str], str], dict[str, dict]]:
    """Link company names across waves, through the scanner's confusions.

    Two stages, because no single similarity threshold can do this job. On this
    corpus the *same* firm ("Compagnie Générale Égyptienne de Pétroles" and its
    mangled twin) scores 88.5 by plain ratio, while two *different* firms
    ("Kafr El Zayat Cotton Co" and "Kafr El Zayat Land Co") score 87.5. The
    distributions overlap, so a threshold on ratio must either merge different
    firms or split the same one.

    1. **Exact skeleton match** (``names.ocr_skeleton``) merges outright.
       Folding characters into the classes the scanner confuses makes "Collan",
       "CoLLan" and "Cotton" one string, while "Land" stays another.
    2. **Weighted edit distance** (``names.ocr_distance``) decides the rest.
       Substituting a character for one it is commonly misread as costs a
       fraction of an arbitrary substitution, so the same firm scanned twice —
       differing by many *cheap* edits — separates from two firms differing by
       few *expensive* ones. Cheap candidates are generated with a fast ratio
       over skeletons, then confirmed with the weighted distance.

    The threshold is set to split rather than merge when uncertain: a false
    split fragments one firm, while a false merge invents ties between two.
    """
    import numpy as np
    from rapidfuzz import fuzz, process

    uniq = sorted({(y, n) for y, n in pairs})
    idx = {p: i for i, p in enumerate(uniq)}
    skeletons = {p: ocr_skeleton(p[1]) for p in uniq}
    letters = {p: company_letters(p[1]) for p in uniq}

    uf = _UnionFind()
    for i in range(len(uniq)):
        uf.find(i)

    # Stage 1: the same firm, read differently.
    by_skeleton: dict[str, list[int]] = defaultdict(list)
    for p, i in idx.items():
        if skeletons[p]:
            by_skeleton[skeletons[p]].append(i)
    for members in by_skeleton.values():
        for other in members[1:]:
            uf.union(members[0], other)

    # Stage 2: near matches, compared once per distinct skeleton.
    #
    # Complete linkage, not single linkage. Chaining A~B and B~C into one
    # cluster is how "Alexandria Life Insurance" ends up merged with
    # "Alexandria Insurance", and "Industrie des Fibres Textiles" with
    # "Société Egyptienne des Industries Textiles": each step is under the
    # threshold while the ends are nowhere near each other. Requiring every
    # cross-pair to stay within *max_diameter* stops a cluster from drifting.
    reps = sorted(by_skeleton)
    rep_pair = {sk: uniq[members[0]] for sk, members in by_skeleton.items()}
    if len(reps) > 1:
        scores = process.cdist(reps, reps, scorer=fuzz.ratio,
                               score_cutoff=candidate_cutoff,
                               dtype=np.uint8, workers=-1)
        a_idx, b_idx = np.nonzero(np.triu(scores, k=1))

        candidates: list[tuple[float, int, int]] = []
        for a, b in zip(a_idx.tolist(), b_idx.tolist()):
            la = letters[rep_pair[reps[a]]]
            lb = letters[rep_pair[reps[b]]]
            if min(len(la), len(lb)) < min_letters:
                continue
            dist = ocr_distance(la, lb)
            if dist > max_distance:
                continue
            # A whole extra word means a different firm: "Alexandria Life
            # Insurance" is not "Alexandria Insurance", though only four
            # letters separate them. But the veto is suspended when the names
            # are already all but identical, because there the odd token is
            # scanner debris — "A lexandria Insurance" loses its stray "A" and
            # would otherwise look like a word the other name lacks.
            if dist > near_identical and unmatched_content_token(
                    rep_pair[reps[a]][1], rep_pair[reps[b]][1]):
                continue
            candidates.append((dist, a, b))
        candidates.sort()  # closest first, so the surest merges happen early

        # Members of each live cluster, as indices into `reps`.
        group_of = {a: [a] for a in range(len(reps))}
        for dist, a, b in candidates:
            ra, rb = uf.find(by_skeleton[reps[a]][0]), uf.find(by_skeleton[reps[b]][0])
            if ra == rb:
                continue
            ma = group_of.setdefault(a, [a])
            mb = group_of.setdefault(b, [b])
            if any(ocr_distance(letters[rep_pair[reps[x]]],
                                letters[rep_pair[reps[y]]]) > max_diameter
                   for x in ma for y in mb):
                continue
            uf.union(by_skeleton[reps[a]][0], by_skeleton[reps[b]][0])
            merged = ma + mb
            for member in merged:
                group_of[member] = merged

    clusters: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for p, i in idx.items():
        clusters[uf.find(i)].append(p)

    mapping: dict[tuple[int, str], str] = {}
    companies: dict[str, dict] = {}
    for n, (_, group) in enumerate(sorted(clusters.items()), start=1):
        cid = f"C{n:05d}"
        # Canonical label: the most frequent printed form, longest breaking
        # ties — the modal spelling is usually the least damaged one.
        counts = Counter(name for _, name in group)
        label = max(counts, key=lambda d: (counts[d], len(d)))
        companies[cid] = {
            "company_id": cid,
            "label": label,
            "name_key": normalize_company(label),
            "skeleton": skeletons[group[0]],
            "variants": sorted({name for _, name in group}),
            "years_present": sorted({y for y, _ in group}),
        }
        for p in group:
            mapping[p] = cid
    return mapping, companies
