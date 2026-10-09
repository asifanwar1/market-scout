import pytest

from app.core.importing.lookup import OvertureLookup, fill_from
from app.core.scouting import place_store
from app.core.scouting.place_store import StoreError
from app.core.scouting.types import RawBusiness

LAHORE = (31.34, 74.14, 31.70, 74.57)
KARACHI = (24.6, 66.8, 25.2, 67.4)


def place(identifier: str, name: str, latitude: float = 31.5, longitude: float = 74.3, **overrides) -> dict:
    data = {
        "id": identifier, "name": name, "categories": ["electronics_store"], "confidence": 0.8,
        "phones": ["+923001234567"], "websites": [], "emails": [], "latitude": latitude, "longitude": longitude,
    }
    data.update(overrides)
    return data


@pytest.fixture()
def lookup(tmp_path):
    path = tmp_path / "o.sqlite"
    place_store.write_store(
        path,
        [
            place("kashif", "Kashif Traders", phones=["+923004309775"], websites=["https://kashif.pk"]),
            place("malik-1", "Malik Traders", latitude=31.50),
            place("malik-2", "MALIK TRADERS (Pvt) Ltd.", latitude=31.55),
            place("khi-malik", "Malik Traders", latitude=24.9, longitude=67.0),
            place("premier", "Premier Energy Pvt Ltd", emails=["info@premier.pk"], phones=[]),
            place("closed", "Closed Solar", status="permanently_closed"),
            place("weak", "Doubtful Solar", confidence=0.1),
            place("empty", "Contactless Shop", phones=[], websites=[], emails=[]),
            place("ali", "Ali", phones=["+923001111111"]),
        ],
        release="2026-09-23.1",
    )
    with OvertureLookup(str(path), min_confidence=0.3) as opened:
        yield opened


def test_an_exact_name_in_the_right_city_is_found_with_its_contacts(lookup):
    found = lookup.find("KASHIF TRADERS", LAHORE)

    assert found.source_key == "overture" and found.external_id == "kashif"
    assert found.phones == ["+923004309775"] and found.website == "https://kashif.pk"


def test_legal_suffixes_and_punctuation_do_not_matter(lookup):
    assert lookup.find("Premier  Energy (Private) Limited", LAHORE).external_id == "premier"
    assert lookup.find("premier energy, pvt. ltd", LAHORE).external_id == "premier"


def test_a_name_that_is_only_nearly_the_same_is_not_a_match(lookup):
    assert lookup.find("Kashif Trader", LAHORE) is None
    assert lookup.find("Kashif Traders International", LAHORE) is None


def test_two_places_with_that_name_in_the_city_are_ambiguous_so_neither_is_used(lookup):
    assert lookup.find("Malik Traders", LAHORE) is None


def test_the_same_name_in_another_city_is_found_only_when_the_row_is_in_that_city(lookup):
    assert lookup.find("Malik Traders", KARACHI).external_id == "khi-malik"
    assert lookup.find("Kashif Traders", KARACHI) is None


def test_without_a_city_the_name_must_be_unique_in_the_whole_country(lookup):
    assert lookup.find("Kashif Traders", None).external_id == "kashif"
    assert lookup.find("Malik Traders", None) is None


@pytest.mark.parametrize("name", ["Closed Solar", "Doubtful Solar", "Contactless Shop", "Nobody At All"])
def test_closed_doubtful_contactless_and_unknown_places_are_not_used(lookup, name):
    assert lookup.find(name, LAHORE) is None


def test_a_very_short_name_means_nothing(lookup):
    assert lookup.find("Ali", LAHORE) is None
    assert lookup.find("", LAHORE) is None


def test_a_missing_data_file_is_an_error_not_silence(tmp_path):
    with pytest.raises(StoreError):
        OvertureLookup(str(tmp_path / "nope.sqlite"), 0.3)


def row(**overrides) -> RawBusiness:
    data = {"source_key": "import:Chamber", "external_id": "x1", "name": "Kashif Traders", "address": "Johar Town, Lahore", "raw": {"Mship": "1-A"}}
    data.update(overrides)
    return RawBusiness(**data)


def test_filling_takes_only_what_the_list_lacked_and_says_where_it_came_from(lookup):
    found = lookup.find("Kashif Traders", LAHORE)

    filled = fill_from(row(), found)

    assert filled.phones == ["+923004309775"] and filled.website == "https://kashif.pk"
    assert (filled.latitude, filled.longitude) == (31.5, 74.3)
    assert filled.name == "Kashif Traders" and filled.address == "Johar Town, Lahore"
    assert filled.source_key == "import:Chamber"
    assert filled.raw["Mship"] == "1-A" and filled.raw["contacts_from"] == {"source": "overture", "id": "kashif"}
    assert "electronics_store" in filled.categories


def test_filling_never_replaces_what_the_list_already_had(lookup):
    found = lookup.find("Kashif Traders", LAHORE)

    filled = fill_from(row(emails=["own@kashif.pk"], website="https://listed.pk", latitude=31.1, longitude=74.1), found)

    assert filled.emails == ["own@kashif.pk"] and filled.website == "https://listed.pk"
    assert (filled.latitude, filled.longitude) == (31.1, 74.1)
