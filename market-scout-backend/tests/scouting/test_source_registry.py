import pytest

from app.core.config import settings
from app.core.scouting.sources.base import KIND_DISCOVERY, SourceBuildContext
from app.core.scouting.sources.registry import CATALOG, build_source, get_source_info, source_label


def context(api_key=None):
    return SourceBuildContext(api_key=api_key, user_agent="test", settings=settings)


def test_every_source_has_its_own_key():
    keys = [info.key for info in CATALOG]
    assert len(keys) == len(set(keys))


def test_every_discovery_source_can_be_built_and_carries_the_key_it_is_listed_under():
    for info in CATALOG:
        if info.kind != KIND_DISCOVERY:
            continue
        built = build_source(info.key, context(api_key="a-key" if info.requires_api_key else None))
        assert built.key == info.key


def test_a_source_that_needs_a_key_refuses_to_be_built_without_one():
    with pytest.raises(ValueError, match="API key"):
        build_source("google_places", context())


def test_an_unknown_or_non_searchable_source_cannot_be_built():
    with pytest.raises(ValueError, match="Unknown discovery source"):
        build_source("nope", context())
    with pytest.raises(ValueError, match="Unknown discovery source"):
        build_source("website_enrichment", context())


def test_dataset_sources_say_where_their_file_is_and_how_to_make_it():
    for key in ("overture", "foursquare"):
        info = get_source_info(key)
        assert info.requires_dataset
        assert info.dataset.path(settings).endswith(".sqlite")
        assert info.dataset.download_command.startswith("python -m scripts.download_")


def test_terms_are_checked_against_each_sources_own_rules():
    unanswerable = {"clauses": [["shop=bakery_not_mapped"]]}
    solar = {"clauses": [["shop=electrical", "name~solar"]]}

    assert get_source_info("osm").supports_term(unanswerable) is True
    assert get_source_info("osm").supports_term(None) is False
    assert get_source_info("overture").supports_term(unanswerable) is False
    assert get_source_info("foursquare").supports_term(unanswerable) is False
    assert get_source_info("foursquare").supports_term(solar) is True
    assert get_source_info("google_places").supports_term(None) is True


def test_source_labels_use_the_catalog_name():
    assert source_label("foursquare") == "Foursquare Places"
    assert source_label("import:Chamber list") == "Chamber list"


def test_paid_sources_declare_their_rate_setting_page_limit_and_search_time():
    expected = (("google_places", "PLACES_COST_PER_REQUEST_USD", 3), ("here", "HERE_COST_PER_REQUEST_USD", 1), ("tomtom", "TOMTOM_COST_PER_REQUEST_USD", 3))
    for key, setting, pages in expected:
        info = get_source_info(key)
        assert info.is_paid and info.cost_per_request_setting == setting and info.max_requests_per_search == pages
        assert info.cost_per_request(settings) == getattr(settings, setting)
        assert info.search_seconds(settings) > 0
        assert info.terms_note


def test_free_sources_cost_nothing_per_request():
    assert get_source_info("foursquare").cost_per_request(settings) == 0.0
    assert get_source_info("overture").search_seconds(settings) == 0.0
    assert get_source_info("osm").search_seconds(settings) > settings.OVERPASS_MIN_INTERVAL_SECONDS
