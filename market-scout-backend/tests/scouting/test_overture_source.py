import sqlite3

import pytest

from app.core.scouting import place_store
from app.core.scouting.sources import overture
from app.core.scouting.sources.base import SourceError
from app.core.scouting.types import SearchArea, SearchQuery

LAHORE = SearchArea(latitude=31.5204, longitude=74.3587, radius_km=20, name="Lahore")
SOLAR = {"clauses": [["shop=electrical", "name~solar|inverter"], ["name~solar"]]}


def place(identifier: str, name: str, category: str = "electronics_store", **overrides) -> dict:
    data = {
        "id": identifier, "name": name, "categories": [category], "confidence": 0.8, "status": None,
        "phones": ["+923001234567"], "websites": [], "emails": [], "socials": [], "address": None, "city": "Lahore",
        "latitude": 31.52, "longitude": 74.36, "dataset": "meta",
    }
    data.update(overrides)
    return data


@pytest.fixture()
def store_path(tmp_path):
    path = tmp_path / "overture.sqlite"
    place_store.write_store(
        path,
        [
            place("a", "Noor Solar Traders"),
            place("b", "Bright Electronics", "electronics_store"),
            place("c", "Inverter Zone", "electronics_store"),
            place("d", "Inverter Zone Karachi", "electronics_store", latitude=24.86, longitude=67.0),
            place("e", "Solar Hub (closed)", status="permanently_closed"),
            place("f", "Faint Solar", confidence=0.1),
            place("g", "Ali Bakery", "bakery"),
            place("h", "Sun Power", "solar_installation", phones=[]),
        ],
        release="2026-09-23.1",
    )
    return str(path)


def search(path, osm_filter=SOLAR, area=LAHORE, min_confidence=0.3):
    source = overture.OvertureSource(path, min_confidence=min_confidence)
    return source.search(SearchQuery(text="x", area=area, osm_filter=osm_filter))


def ids(result):
    return {business.external_id for business in result.businesses}


def test_a_shop_tag_becomes_overture_categories_and_a_name_pattern_stays_a_pattern():
    (clause,) = overture.translate_filter({"clauses": [["shop=electrical", "name~solar|inverter"]]})

    assert "electronics_store" in clause.categories and "solar_installation" in clause.categories
    assert clause.name_patterns == ("solar|inverter",)


def test_a_name_only_group_has_no_category_limit():
    (clause,) = overture.translate_filter({"clauses": [["name~solar"]]})
    assert clause.categories is None and clause.name_patterns == ("solar",)


def test_two_tags_in_one_group_must_both_hold():
    assert overture.translate_filter({"clauses": [["craft=electrician", "shop=hardware"]]}) == []
    (clause,) = overture.translate_filter({"clauses": [["shop=electrical", "craft=electrician"]]})
    assert clause.categories == frozenset({"electrician"})


@pytest.mark.parametrize(
    "osm_filter",
    [
        None,
        {},
        {"clauses": []},
        {"clauses": [["office=company"]]},
        {"clauses": [["shop=bakery_not_mapped"]]},
        {"clauses": [["shop=electrical", "unknown_key=1"]]},
        {"clauses": [["name~(unclosed"]]},
        {"clauses": [["not a condition"]]},
    ],
)
def test_groups_that_cannot_be_answered_make_the_term_unsupported(osm_filter):
    assert overture.supports(osm_filter) is False


def test_one_answerable_group_is_enough_and_the_others_are_dropped():
    clauses = overture.translate_filter({"clauses": [["shop=bakery_not_mapped"], ["name~solar"]]})
    assert [clause.name_patterns for clause in clauses] == [("solar",)]


def test_office_company_with_a_name_pattern_is_name_only():
    (clause,) = overture.translate_filter({"clauses": [["office=company", "name~electric|contractor"]]})
    assert clause.categories is None and clause.name_patterns == ("electric|contractor",)


def test_every_seeded_solar_term_with_an_osm_filter_can_be_searched_in_overture():
    from scripts.seed_data.solar_profile import build_solar_profile

    for term in build_solar_profile().search_terms:
        if term.osm_filter:
            assert overture.supports(term.osm_filter.model_dump()), term.text


def test_finds_places_by_name_and_by_category_inside_the_city_only(store_path):
    result = search(store_path)
    assert ids(result) == {"a", "c"}


def test_a_category_in_the_filter_alone_finds_places_without_a_matching_name(store_path):
    result = search(store_path, {"clauses": [["shop=electronics"]]})
    assert ids(result) == {"a", "b", "c"}


def test_closed_and_low_confidence_places_are_left_out(store_path):
    assert "e" not in ids(search(store_path)) and "f" not in ids(search(store_path))
    assert "f" in ids(search(store_path, min_confidence=0.0))


def test_names_are_matched_without_regard_to_case(store_path):
    assert "a" in ids(search(store_path, {"clauses": [["name~SOLAR traders"]]}))


def test_an_underscore_in_a_category_is_not_a_wildcard(tmp_path):
    path = tmp_path / "o.sqlite"
    place_store.write_store(
        path, [place("real", "Real Shop", "electronics_store"), place("lookalike", "Fake Shop", "electronicsXstore")], release="r"
    )
    assert ids(search(str(path), {"clauses": [["shop=electronics"]]})) == {"real"}


def test_a_pattern_with_quotes_is_just_text_not_sql(store_path):
    assert search(store_path, {"clauses": [["name~x'; DROP TABLE places;--"]]}).businesses == []
    assert ids(search(store_path)) == {"a", "c"}


def test_results_are_best_confidence_first(store_path):
    path = store_path
    place_store.write_store(
        path, [place("low", "Solar A", confidence=0.4), place("high", "Solar B", confidence=0.9)], release="r"
    )
    assert [business.external_id for business in search(path).businesses] == ["high", "low"]


def test_a_search_makes_no_requests_and_an_unsupported_term_finds_nothing(store_path):
    assert search(store_path).requests_made == 0
    empty = search(store_path, {"clauses": [["shop=bakery_not_mapped"]]})
    assert empty.businesses == [] and empty.requests_made == 0


def test_a_place_becomes_a_lead_with_its_contacts_and_provenance(tmp_path):
    path = tmp_path / "o.sqlite"
    place_store.write_store(
        path,
        [
            place(
                "gers-1", "Noor Solar", "solar_installation", address="12 Mall Road", city="Lahore",
                phones=["+923001234567", "+924235551234"], emails=["info@noor.pk"], websites=[],
                socials=["https://www.facebook.com/noor"],
            ),
            place("gers-2", "Beta Solar", "solar_installation", address="Gulberg, Lahore", city="Lahore", websites=["https://beta.pk"]),
        ],
        release="2026-09-23.1",
    )
    by_id = {business.external_id: business for business in search(str(path)).businesses}

    first = by_id["gers-1"]
    assert first.source_key == "overture" and first.name == "Noor Solar"
    assert first.phones == ["+923001234567", "+924235551234"] and first.emails == ["info@noor.pk"]
    assert first.website == "https://www.facebook.com/noor"
    assert first.address == "12 Mall Road, Lahore"
    assert first.categories == ["solar_installation"]
    assert first.raw["release"] == "2026-09-23.1" and first.raw["dataset"] == "meta"
    assert (first.latitude, first.longitude) == (31.52, 74.36)

    second = by_id["gers-2"]
    assert second.website == "https://beta.pk"
    assert second.address == "Gulberg, Lahore"


def test_a_missing_file_is_a_source_error_with_a_plain_message(tmp_path):
    with pytest.raises(SourceError, match="not been downloaded"):
        search(str(tmp_path / "nope.sqlite"))


def test_test_connection_reports_the_release_and_size_or_what_is_wrong(store_path, tmp_path):
    ok, message = overture.OvertureSource(store_path).test_connection()
    assert ok and "2026-09-23.1" in message and "8 places" in message

    ok, message = overture.OvertureSource(str(tmp_path / "nope.sqlite")).test_connection()
    assert not ok and "not been downloaded" in message


def test_a_file_from_an_older_layout_has_to_be_downloaded_again(tmp_path):
    path = tmp_path / "old.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL); INSERT INTO meta VALUES ('schema_version', '0');")
    connection.commit()
    connection.close()

    with pytest.raises(place_store.StoreError, match="older version"):
        place_store.read_info(path)


def test_a_file_that_is_not_a_database_is_reported_not_crashed_on(tmp_path):
    path = tmp_path / "junk.sqlite"
    path.write_bytes(b"this is not a database at all" * 50)

    with pytest.raises(place_store.StoreError, match="can't be read"):
        place_store.read_info(path)


def test_a_failed_rebuild_leaves_the_previous_file_untouched(tmp_path):
    path = tmp_path / "o.sqlite"
    place_store.write_store(path, [place("a", "Solar A")], release="old")

    def broken():
        yield place("b", "Solar B")
        raise RuntimeError("network dropped")

    with pytest.raises(RuntimeError):
        place_store.write_store(path, broken(), release="new")

    assert place_store.read_info(path).release == "old"
    assert not (tmp_path / "o.sqlite.building").exists()


def test_rebuilding_replaces_the_data_and_the_release(tmp_path):
    path = tmp_path / "o.sqlite"
    place_store.write_store(path, [place("a", "Solar A")], release="old")
    count = place_store.write_store(path, [place("a", "Solar A"), place("b", "Solar B")], release="new")

    info = place_store.read_info(path)
    assert count == 2 and (info.release, info.places) == ("new", 2)


def test_the_file_is_opened_read_only(store_path):
    connection = place_store.connect(store_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM places")
    finally:
        connection.close()
