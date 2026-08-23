"""Name decomposition and transliteration folding.

The real name strings here exercise the normaliser against variants actually
attested in French-language Egyptian directories. They are string-normalisation
assertions, not claims about anyone's directorships.
"""

import pytest

from politi.names import normalize_company, normalize_name, parse_person


@pytest.mark.parametrize("variants", [
    ("Cattaui", "Cattaoui", "Qattawi"),
    ("Sidky", "Sidki", "Sidqi"),
    ("Abboud", "Aboud", "Abbud"),
    ("Nahas", "Nahhas"),
    ("Chérif", "Sherif"),
    ("Mohamed", "Mohammed"),
])
def test_transliteration_variants_share_a_key(variants):
    keys = {normalize_name(v) for v in variants}
    assert len(keys) == 1, f"{variants} -> {keys}"


def test_distinct_surnames_keep_distinct_keys():
    assert normalize_name("Cattaui") != normalize_name("Menasce")
    assert normalize_name("Sidky") != normalize_name("Serry")


@pytest.mark.parametrize("raw,display,rank,prefix", [
    ("S.E. Ismaïl Sidky Pacha", "Ismaïl Sidky", "pasha", "s.e."),
    ("M. Joseph A. Cattaui Bey", "Joseph A. Cattaui", "bey", "m."),
    ("Élie N. Mosseri", "Élie N. Mosseri", None, None),
    ("Hassan Effendi", "Hassan", "effendi", None),
    ("Sir Aubrey Wintersham", "Aubrey Wintersham", None, "sir"),
])
def test_decomposition(raw, display, rank, prefix):
    p = parse_person(raw)
    assert p.display == display
    assert p.rank == rank
    assert p.prefix == prefix


def test_rank_is_stripped_from_the_matching_key():
    """A director promoted between volumes must still match themselves."""
    bey = parse_person("M. Ahmed Abboud Bey")
    pacha = parse_person("S.E. Ahmed Abboud Pacha")
    assert bey.key == pacha.key
    assert (bey.rank, pacha.rank) == ("bey", "pasha")


def test_nobiliary_particles_are_dropped_from_the_key():
    assert normalize_name("de Menasce") == normalize_name("Menasce")


def test_company_key_ignores_legal_form():
    a = normalize_company("Société Anonyme des Eaux du Caire")
    b = normalize_company("Compagnie des Eaux du Caire")
    assert a == b == "eaux caire"
