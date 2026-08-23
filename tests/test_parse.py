"""Parsing an annuaire volume. Uses the synthetic fixture; see fixtures/README.md."""

from pathlib import Path

import pytest

from politi.parse import (
    parse_capital, parse_company_block, parse_volume, split_person_list,
)

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_volume.txt"


@pytest.fixture(scope="module")
def volume():
    return parse_volume(FIXTURE.read_text(encoding="utf-8"))


def test_finds_every_company_entry(volume):
    assert len(volume) == 3
    assert volume[0].name.startswith("SOCIETE ANONYME FICTIVE DES EAUX")


def test_front_matter_is_not_mistaken_for_a_company(volume):
    names = [c.name for c in volume]
    assert not any("SOMMAIRE" in n or "ANNUAIRE" in n for n in names)


def test_company_fields(volume):
    eaux = volume[0]
    assert eaux.city == "Cairo"
    assert (eaux.capital_currency, eaux.capital_amount) == ("LE", 500_000.0)
    assert eaux.founded == "12 mai 1928"
    assert eaux.source_page == 2


def test_roles_are_mapped_to_the_controlled_vocabulary(volume):
    roles = [d.role for d in volume[0].directorships]
    assert roles[:3] == ["president", "vice_president", "managing_director"]
    assert roles.count("director") == 4
    assert roles.count("auditor") == 2


def test_ranks_survive_parsing(volume):
    by_name = {d.person.display: d.person.rank for d in volume[0].directorships}
    assert by_name["Faridoun Zohdy"] == "pasha"
    assert by_name["Gaston R. Palamède"] == "bey"
    assert by_name["Théodule N. Vasconi"] is None


def test_rosters_wrapping_across_lines_are_kept_whole(volume):
    """The 'Administrateurs' list in entry 1 runs onto a second printed line."""
    directors = [d.person.display for d in volume[0].directorships if d.role == "director"]
    assert "Ismaïl Berkouk" in directors
    assert "Aubrey Wintersham" in directors


def test_a_following_role_label_does_not_leak_into_the_previous_roster(volume):
    """Regression: 'Directeur Général' once got swallowed into a director name."""
    sucreries = volume[1]
    assert all("Directeur" not in d.person.display for d in sucreries.directorships)
    assert any(d.role == "general_manager" for d in sucreries.directorships)


@pytest.mark.parametrize("raw,expected", [
    ("L.E. 500.000", ("LE", 500_000.0)),
    ("L.E. 1.250.000", ("LE", 1_250_000.0)),
    ("£E 250.000", ("LE", 250_000.0)),
    ("Frs. 25.000.000", ("FRF", 25_000_000.0)),
])
def test_capital_parsing(raw, expected):
    assert parse_capital(raw) == expected


def test_person_list_splitting():
    got = split_person_list("MM. Ahmed Abboud Pacha, Élie N. Mosseri et Henri Naus Bey")
    assert got == ["Ahmed Abboud Pacha", "Élie N. Mosseri", "Henri Naus Bey"]


def test_parenthetical_glosses_are_dropped():
    got = split_person_list("MM. Jean Dupont (démissionnaire), Paul Durand")
    assert got == ["Jean Dupont", "Paul Durand"]


def test_block_without_a_board_is_skipped():
    comp = parse_company_block("SOCIETE SANS CONSEIL", "Siège social : Le Caire.\n")
    assert comp.directorships == []
