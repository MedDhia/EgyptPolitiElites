"""Coding directors by community of origin."""

import pytest

from politi.origin import ARAB, EUROPEAN, MINORITY, UNKNOWN, classify, is_person


@pytest.mark.parametrize("name,expected", [
    ("S.E. Cattaui Pacha Joseph A.", MINORITY),      # Egyptian Jewish
    ("Mosseri Elie N", MINORITY),
    ("Choremi Constantin Jean", MINORITY),           # Greek
    ("Tanielian Berge", MINORITY),                   # Armenian
    ("Sursock Wladimir", MINORITY),                  # Syro-Lebanese
    ("Naus Bey Henri C.B.E.", EUROPEAN),             # Belgian
    ("Barker Henry", EUROPEAN),                      # British
    ("Abdel Hamid Badaoui Pacha", ARAB),
    ("Mohamed Mahmoud Bey Khalil", ARAB),
    ("Ahmed Abboud Pacha", ARAB),
])
def test_known_directors(name, expected):
    assert classify(name).group == expected


def test_a_european_given_name_is_not_evidence_of_european_origin():
    """Regression: 'nicolas' sat in a French surname lexicon, so Bassili — a
    Copt — was classified European. The contrast under study is European vs
    Egyptian, so this error pushed straight on the estimand."""
    assert classify("Bassili Nicolas Alexandre").group == MINORITY
    assert classify("Joseph Cattaui").group == MINORITY
    assert classify("Élie Mosseri").group == MINORITY


def test_titles_are_not_evidence_of_origin():
    """Bey and Pacha were held across every community here."""
    assert classify("Barker Bey Henry").group == EUROPEAN
    assert classify("Cattaui Pacha Joseph").group == MINORITY


def test_unclassifiable_names_are_not_guessed():
    assert classify("Xqzv Wprt").group == UNKNOWN
    assert classify("").group == UNKNOWN


@pytest.mark.parametrize("junk", [
    "Grand Officier Couronne Belge", "Ancien Ministre", "Le Caire",
    "Linen Industry", "Comité Gouvernemental des Textiles",
    "Etudes: American College Smyrne", "Nil B.A. Oxford University F.R.G.S",
])
def test_non_persons_are_excluded(junk):
    assert not is_person(junk)


@pytest.mark.parametrize("real", [
    "Cattaui Pacha Joseph A.", "Barker Henry", "Abdel Hamid Badaoui",
])
def test_real_directors_survive_the_filter(real):
    assert is_person(real)
