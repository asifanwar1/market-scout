import pytest

from app.core.scouting import place_store
from app.core.scouting.sources import foursquare
from app.core.scouting.sources.base import SourceError
from app.core.scouting.types import SearchArea, SearchQuery

LAHORE = SearchArea(latitude=31.5204, longitude=74.3587, radius_km=20, name="Lahore")
SOLAR = {"clauses": [["shop=electrical", "name~solar|inverter"], ["name~solar"]]}
ELECTRONICS_STORE = "Retail > Electronics Store"


def place(identifier: str, name: str, category: str = ELECTRONICS_STORE, **overrides) -> dict:
    data = {
        "id": identifier, "name": name, "categories": [category], "confidence": 1.0, "status": None,
        "phones": ["03001234567"], "websites": [], "emails": [], "socials": [], "address": None, "city": "Lahore",
        "latitude": 31.52, "longitude": 74.36, "dataset": "foursquare",
    }
    data.update(overrides)
    return data


@pytest.fixture()
def store_path(tmp_path):
    path = tmp_path / "foursquare.sqlite"
    place_store.write_store(
        path,
        [
            place("a", "Noor Solar Traders"),
            place("b", "Bright Electronics"),
            place("c", "Inverter Zone"),
            place("d", "Inverter Zone Karachi", latitude=24.86, longitude=67.0),
            place("e", "Solar Hub (closed)", status=place_store.STATUS_PERMANENTLY_CLOSED),
            place("g", "Ali Bakery", "Dining and Drinking > Bakery"),
            place("h", "Sun Power", "Business and Professional Services > Solar Installation", phones=[]),
        ],
        release="2026-09-30",
    )
    return str(path)


def search(path, osm_filter=SOLAR, area=LAHORE):
    return foursquare.FoursquareSource(path).search(SearchQuery(text="x", area=area, osm_filter=osm_filter))


def ids(result):
    return {business.external_id for business in result.businesses}


def test_a_shop_tag_becomes_category_keywords_and_a_name_pattern_stays_a_pattern():
    (clause,) = foursquare.translate_filter({"clauses": [["shop=electrical", "name~solar|inverter"]]})

    assert {"electronics store", "electrician", "solar"} <= clause.categories
    assert clause.name_patterns == ("solar|inverter",)


@pytest.mark.parametrize(
    "osm_filter",
    [None, {}, {"clauses": []}, {"clauses": [["office=company"]]}, {"clauses": [["shop=bakery_not_mapped"]]}, {"clauses": [["name~(unclosed"]]}],
)
def test_groups_that_cannot_be_answered_make_the_term_unsupported(osm_filter):
    assert foursquare.supports(osm_filter) is False


def test_every_seeded_solar_term_with_an_osm_filter_can_be_searched_in_foursquare():
    from scripts.seed_data.solar_profile import build_solar_profile

    for term in build_solar_profile().search_terms:
        if term.osm_filter:
            assert foursquare.supports(term.osm_filter.model_dump()), term.text


def test_finds_places_by_name_and_by_category_inside_the_city_only(store_path):
    assert ids(search(store_path)) == {"a", "c"}


def test_a_category_in_the_filter_alone_finds_places_without_a_matching_name(store_path):
    assert ids(search(store_path, {"clauses": [["shop=electronics"]]})) == {"a", "b", "c"}


def test_categories_are_matched_by_keyword_without_regard_to_case(tmp_path):
    path = tmp_path / "f.sqlite"
    place_store.write_store(
        path, [place("shout", "Loud Shop", "RETAIL > ELECTRONICS STORE"), place("other", "Other Shop", "Retail > Bakery")], release="r"
    )
    assert ids(search(str(path), {"clauses": [["shop=electronics"]]})) == {"shout"}


def test_closed_places_are_left_out(store_path):
    assert "e" not in ids(search(store_path))


def test_a_pattern_with_quotes_is_just_text_not_sql(store_path):
    assert search(store_path, {"clauses": [["name~x'; DROP TABLE places;--"]]}).businesses == []
    assert ids(search(store_path)) == {"a", "c"}


def test_a_search_makes_no_requests_and_an_unsupported_term_finds_nothing(store_path):
    assert search(store_path).requests_made == 0
    empty = search(store_path, {"clauses": [["shop=bakery_not_mapped"]]})
    assert empty.businesses == [] and empty.requests_made == 0


def test_a_place_becomes_a_lead_with_its_contacts_and_provenance(tmp_path):
    path = tmp_path / "f.sqlite"
    place_store.write_store(
        path,
        [
            place(
                "fsq-1", "Noor Solar", "Business and Professional Services > Solar Installation", address="12 Mall Road",
                phones=["03001234567"], emails=["info@noor.pk"], socials=["https://www.facebook.com/noor"],
            ),
            place("fsq-2", "Beta Solar", address="Gulberg, Lahore", websites=["https://beta.pk"]),
        ],
        release="2026-09-30",
    )
    by_id = {business.external_id: business for business in search(str(path)).businesses}

    first = by_id["fsq-1"]
    assert first.source_key == "foursquare" and first.name == "Noor Solar"
    assert first.phones == ["03001234567"] and first.emails == ["info@noor.pk"]
    assert first.website == "https://www.facebook.com/noor"
    assert first.address == "12 Mall Road, Lahore"
    assert first.categories == ["Business and Professional Services > Solar Installation"]
    assert first.raw["release"] == "2026-09-30" and first.raw["dataset"] == "foursquare"
    assert (first.latitude, first.longitude) == (31.52, 74.36)

    second = by_id["fsq-2"]
    assert second.website == "https://beta.pk"
    assert second.address == "Gulberg, Lahore"


def test_a_missing_file_is_a_source_error_with_a_plain_message(tmp_path):
    with pytest.raises(SourceError, match="not been downloaded"):
        search(str(tmp_path / "nope.sqlite"))


def test_test_connection_reports_the_release_and_size_or_what_is_wrong(store_path, tmp_path):
    ok, message = foursquare.FoursquareSource(store_path).test_connection()
    assert ok and message == "Foursquare 2026-09-30: 7 places on this computer"

    ok, message = foursquare.FoursquareSource(str(tmp_path / "nope.sqlite")).test_connection()
    assert not ok and "not been downloaded" in message
