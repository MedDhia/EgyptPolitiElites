"""Parsing the biographical roster of directors.

The strings here are drawn from the real volumes, OCR damage included, because
every one of these cases cost a bug when it was first met.
"""

import pytest

from politi.biographies import (
    _looks_like_given_names, is_running_head, join_lines, parse_entry,
    repair_ocr_spacing,
)


def _orgs(entry):
    return [(p.role, p.organisation) for p in parse_entry(entry).positions]


# --- name formats differ between volumes ------------------------------------

def test_direct_name_order_1932_style():
    b = parse_entry("Cattaui René Bey, Directeur Général de la S. A. du Wadi Kom Ombo.")
    assert b.name == "Cattaui René Bey"


def test_inverted_name_order_1938_1942_1950_style():
    """'Adda, Achille, …' must not reduce to the surname alone."""
    b = parse_entry("Adda, Achille, Administrateur de la S.A. du Béhéra.")
    assert b.name == "Adda Achille"


def test_parenthesised_rank_is_folded_into_the_name():
    b = parse_entry("Allam, Mohamed (Bey), Membre du Conseil d'Administration "
                    "de la Société Egyptienne.")
    assert b.name == "Allam Mohamed Bey"


def test_a_role_is_never_mistaken_for_a_given_name():
    assert not _looks_like_given_names("Directeur Général de la S. A. du Wadi")
    assert not _looks_like_given_names("Adm. Sté. Al Chark pour la Filature")
    assert _looks_like_given_names("Achille")
    assert _looks_like_given_names("Fernand C.A.")
    assert _looks_like_given_names("Mohamed (Bey)")


# --- roles -------------------------------------------------------------------

def test_administrateur_de_is_an_ordinary_directorship():
    """Regression: 'Administrateur de la S.A.' once matched the
    'Administrateur-Gérant' pattern and relabelled every director."""
    assert _orgs("Adda, Achille, Administrateur de la S.A. du Béhéra.") == [
        ("director", "S.A. du Béhéra")]


def test_administrateur_delegue_is_distinguished():
    roles = [r for r, _ in _orgs("Adda, A., Administrateur-Délégué de la Banque Misr.")]
    assert roles == ["managing_director"]


def test_abbreviated_roles_1947_style():
    assert _orgs("Abdel Razzak Aly Hamed, Adm. Sté. Al Chark pour la Filature.") == [
        ("director", "Sté. Al Chark pour la Filature")]


def test_president_du_conseil_does_not_leak_into_the_firm():
    """'Président du Conseil d'Administration de X' names X, not
    'Administration de X'."""
    assert _orgs("Barker Henry, Président du Conseil d'Administration "
                 "de The New Egyptian Cy.") == [("president", "The New Egyptian Cy")]


def test_two_roles_over_one_firm():
    got = _orgs("Baehler Charles, Président du Conseil d'Administration et "
                "Administrateur-Délégué de The Egyptian Hotels Ltd.")
    assert set(got) == {("president", "The Egyptian Hotels Ltd"),
                        ("managing_director", "The Egyptian Hotels Ltd")}


def test_a_bare_de_clause_inherits_the_previous_role():
    got = _orgs("Barker Henry, Membre du Conseil d'Administration de The "
                "Alexandria Water Cy; de la Filature Nationale d'Egypte.")
    assert got == [("director", "The Alexandria Water Cy"),
                   ("director", "Filature Nationale d'Egypte")]


def test_public_bodies_are_flagged_as_non_firms():
    positions = parse_entry(
        "Klat Jules, Membre de la Commission de la Bourse de Minet El Bassal."
    ).positions
    assert positions and not positions[0].is_firm


# --- OCR damage --------------------------------------------------------------

@pytest.mark.parametrize("damaged,clean", [
    ("de Ia Ban que de Crédit", "de la Banque de Crédit"),
    ("la Socié té Générale", "la Société Générale"),
])
def test_ocr_spacing_and_article_repair(damaged, clean):
    assert repair_ocr_spacing(damaged) == clean


def test_running_heads_are_dropped():
    assert is_running_head("516 .\\:-.INUA!RE DES SOClÉTÉS ÉGYPTIENNES PAR ACTIONS")
    assert not is_running_head("Adda, Achille, Administrateur de la S.A.")


def test_words_broken_across_lines_are_rejoined_without_a_space():
    joined = join_lines("Cattaui René Bey, Administrateur de la Na\ntional Insurance Cy.")
    assert "National Insurance" in joined


def test_a_real_word_boundary_keeps_its_space():
    joined = join_lines("Cattaui René Bey, Membre du\nConseil d'Administration de X.")
    assert "Membre du Conseil" in joined


def test_each_entry_becomes_its_own_line():
    text = ("Adda, Achille, Administrateur de la S.A. du Béhéra.\n"
            "Adda, Me. Charles, Président de la Banque Misr.\n")
    assert len(join_lines(text).split("\n")) == 2


def test_elided_article_keeps_its_space_when_lines_join():
    """Regression: 'Conseil' + 'd'Administration' joined tight produced
    'Conseild'Administration', and the role pattern then ate the 'd',
    leaving "'Administration de X" as the firm name."""
    joined = join_lines("Abboud Mohamed, Président du Conseil\n"
                        "d'Administration de The Egyptian General Omnibus Co.")
    assert "Conseil d'Administration" in joined
    assert _orgs(joined) == [("president", "The Egyptian General Omnibus Co")]


def test_a_government_administration_is_not_a_firm():
    positions = parse_entry(
        "Abdel Hadi Mohamed Bey, Directeur de l'Administration des "
        "Contributions Directes."
    ).positions
    assert positions and not positions[0].is_firm


def test_a_company_fragment_never_starts_an_entry():
    """A continuation line opening with a company name is shaped like an entry
    start. Treating it as one invents a person and truncates the real entry."""
    from politi.biographies import _looks_like_person
    for fragment in ("Copper Works", "Enterprise & Development Co", "Land Cy",
                     "Textile", "Propriétaire National Hotel Cairo"):
        assert not _looks_like_person(fragment), fragment
    for person in ("Cattaui René Bey", "Adda Achille", "Abaza", "Klat Jules"):
        assert _looks_like_person(person), person


def test_a_split_entry_rejoins_rather_than_forking():
    text = ("Sadek Wahba Pacha, Administrateur de la Société Misr de Filature\n"
            "Copper Works, Administrateur de la Société Misr d'Egrenage.\n")
    lines = join_lines(text).split("\n")
    assert len(lines) == 1, "the company fragment must not open a second entry"
