"""Cross-wave entity resolution."""

from politi.names import parse_person
from politi.resolve import Mention, cluster_companies, cluster_persons


def _m(i, year, name, company="ACME", role="director"):
    return Mention(mention_id=i, year=year, company=company, role=role,
                   order=1, person=parse_person(name))


def test_same_person_across_waves_gets_one_id():
    ms = [
        _m(0, 1932, "M. Joseph A. Cattaui Bey"),
        _m(1, 1938, "S.E. Joseph A. Cattaoui Pacha"),
        _m(2, 1947, "Joseph Qattawi Pacha"),
    ]
    mapping, people = cluster_persons(ms)
    assert len({mapping[m.mention_id] for m in ms}) == 1
    pid = mapping[0]
    assert people[pid]["years_present"] == [1932, 1938, 1947]
    assert people[pid]["highest_rank"] == "pasha"


def test_promotion_is_recorded_per_year():
    ms = [_m(0, 1932, "M. Ahmed Abboud Bey"), _m(1, 1947, "S.E. Ahmed Abboud Pacha")]
    mapping, people = cluster_persons(ms)
    pid = mapping[0]
    assert people[pid]["rank_by_year"] == {1932: "bey", 1947: "pasha"}


def test_different_given_names_do_not_merge():
    """Relatives sharing a surname are the main false-positive risk."""
    ms = [_m(0, 1932, "Joseph A. Cattaui"), _m(1, 1932, "René Cattaui")]
    mapping, _ = cluster_persons(ms)
    assert mapping[0] != mapping[1]


def test_an_initial_is_compatible_with_the_spelled_out_given_name():
    ms = [_m(0, 1932, "J. Cattaui"), _m(1, 1938, "Joseph Cattaui")]
    mapping, _ = cluster_persons(ms)
    assert mapping[0] == mapping[1]


def test_unrelated_surnames_stay_apart():
    ms = [_m(0, 1932, "Élie N. Mosseri"), _m(1, 1932, "Élie N. Menasce")]
    mapping, _ = cluster_persons(ms)
    assert mapping[0] != mapping[1]


def test_company_linkage_across_waves():
    pairs = [
        (1932, "SOCIETE ANONYME DES EAUX DU CAIRE"),
        (1938, "Société Anonyme des Eaux du Caire"),
        (1947, "COMPAGNIE DES EAUX DU CAIRE"),
        (1947, "SOCIETE DES CIMENTS D'ALEXANDRIE"),
    ]
    mapping, firms = cluster_companies(pairs)
    eaux = {mapping[p] for p in pairs[:3]}
    assert len(eaux) == 1
    assert mapping[pairs[3]] not in eaux
    assert firms[mapping[pairs[0]]]["years_present"] == [1932, 1938, 1947]


def test_the_abbreviation_rule_still_respects_the_initial_gate():
    """'J. Cattaui' may absorb 'Joseph Cattaui' but never 'René Cattaui'."""
    ms = [_m(0, 1932, "J. Cattaui"), _m(1, 1938, "Joseph Cattaui"),
          _m(2, 1947, "René Cattaui")]
    mapping, _ = cluster_persons(ms)
    assert mapping[0] == mapping[1]
    assert mapping[2] != mapping[0]
