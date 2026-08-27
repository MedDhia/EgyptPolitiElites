"""Coding public office out of the roster entries."""

import pandas as pd
import pytest

from politi.biographies import parse_entry
from politi.politics import (attach_offices, find_offices, firm_flags,
                             person_flags)


@pytest.mark.parametrize("entry,expected", [
    # A portfolio is cabinet; the qualifier makes it past.
    ("Ancien Ministre des Finances", {"cabinet": True}),
    ("Ministre des Wakfs", {"cabinet": False}),
    # Both chambers.
    ("Sénateur du Royaume", {"parliament": False}),
    ("Ancien Député de Gamalieh", {"parliament": True}),
    # A diplomatic 'ministre' is not a cabinet post.
    ("Ministre Plénipotentiaire", {"diplomatic": False}),
    ("Ancien Ministre d'Egypte à Paris", {"diplomatic": True}),
    # Provincial administration, and the two things that borrow its word.
    ("Ancien Gouverneur de la Ville d'Alexandrie", {"provincial": True}),
    ("Moudir d'Assouan", {"provincial": False}),
    ("Gouverneur de la National Bank of Egypt", {}),
    ("Ancien Gouverneur du 83ème District du Rotary Club", {}),
    # Bench and town hall.
    ("Ancien Magistrat", {"judicial": True}),
    ("Ancien Conseiller Municipal", {"municipal": True}),
    # A plain directorship names no office.
    ("Administrateur de la Sté. Anonyme des Ciments", {}),
])
def test_find_offices(entry, expected):
    assert find_offices(entry) == expected


def test_two_offices_in_one_entry():
    found = find_offices("Sénateur; ancien Ministre; Vice-Président de X")
    assert found == {"parliament": False, "cabinet": True}


def test_office_is_not_part_of_the_name():
    """The user-visible half of the same fact: names carry no offices."""
    for entry, name in [
            ("S.E. Sadek, Wahba (Pacha),Sénateur; ancien Ministre; Adm. de X",
             "Sadek Wahba Pacha"),
            ("Abdel Haï Khalil Bey Député, Adm. de la Sté. X",
             "Abdel Haï Khalil Bey"),
            ("Nakhla Pacha El Motei Ancien Magistrat, Prés. de X",
             "Nakhla Pacha El Motei"),
            # A surname that happens to be an honour word survives intact.
            ("Chevalier, Paul, Adm. de la Sté. X", "Chevalier Paul"),
    ]:
        assert parse_entry(entry).name == name


def test_attach_and_flags():
    offices = pd.DataFrame([
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha",
         "office": "cabinet", "former": True, "source_page": 4884},
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha",
         "office": "parliament", "former": False, "source_page": 4884},
    ])
    # Two mentions of the same man: his ministry must not be counted twice.
    crosswalk = pd.DataFrame([
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha", "person_id": "p1"},
        {"year": 1947, "printed_name": "S.E. Sadek Wahba Pacha", "person_id": "p1"},
    ])
    resolved = attach_offices(offices, crosswalk)
    assert len(resolved) == 2

    flags = person_flags(resolved)
    row = flags.iloc[0]
    assert row.n_offices == 2 and row.political and row.national
    assert not row.all_former          # the senate seat is current

    aff = pd.DataFrame([
        {"year": 1947, "person_id": "p1", "company_id": "c1"},
        {"year": 1947, "person_id": "p2", "company_id": "c1"},
        {"year": 1947, "person_id": "p2", "company_id": "c2"},
    ])
    firms = firm_flags(aff, flags).set_index("company_id")
    assert bool(firms.loc["c1", "connected"])
    assert firms.loc["c1", "share_political"] == 0.5
    assert not bool(firms.loc["c2", "connected"])


def test_flags_are_empty_not_broken_without_offices():
    flags = person_flags(pd.DataFrame(columns=["year", "person_id", "office",
                                               "former"]))
    assert flags.empty and "political" in flags.columns
