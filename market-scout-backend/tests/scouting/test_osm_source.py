import httpx
import pytest

from app.core.scouting.sources.base import (
    SourceAuthError,
    SourceRateLimitError,
    SourceUnavailableError,
    request_with_retries,
)
from app.core.scouting.sources.osm import OsmSource, build_overpass_query, parse_elements
from app.core.scouting.types import SearchArea, SearchQuery

LAHORE = SearchArea(latitude=31.5204, longitude=74.3587, radius_km=20, name="Lahore")
FILTER = {"clauses": [["shop=electrical", "name~solar|inverter"], ["name~solar"]]}


def make_source(handler, sleeps=None, clock=None, min_interval=3.0):
    sleeps = sleeps if sleeps is not None else []
    return OsmSource(
        endpoint="https://overpass.test/api/interpreter",
        user_agent="test",
        min_interval_s=min_interval,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleeps.append,
        clock=clock or (lambda: 0.0),
    )


def test_builds_overpass_query_from_clauses_using_a_bounding_box_not_a_radius():
    ql = build_overpass_query(FILTER, LAHORE)
    assert "around" not in ql
    assert ql == (
        '[out:json][timeout:60];\n(\n'
        '  nwr["shop"="electrical"]["name"~"solar|inverter",i](31.34074,74.14794,31.70006,74.56946);\n'
        '  nwr["name"~"solar",i](31.34074,74.14794,31.70006,74.56946);\n'
        ');\nout center tags 1000;'
    )


def test_explicit_bbox_replaces_the_radius_square():
    area = SearchArea(31.5, 74.3, 20, bbox=(31.3, 74.1, 31.7, 74.6))
    assert "(31.30000,74.10000,31.70000,74.60000)" in build_overpass_query({"clauses": [["shop=electrical"]]}, area)


def test_radius_square_is_centred_and_scaled_for_latitude():
    south, west, north, east = LAHORE.rectangle
    assert (south + north) / 2 == pytest.approx(LAHORE.latitude)
    assert (west + east) / 2 == pytest.approx(LAHORE.longitude)
    assert north - south == pytest.approx(2 * 20 / 111.32)
    assert east - west > north - south


@pytest.mark.parametrize(
    "condition",
    ['name~x"];out;//', "shop=a;b", "shop=a\\b", "name~a[b]", "just words", "=v"],
)
def test_query_builder_refuses_unsafe_or_malformed_conditions(condition):
    with pytest.raises(ValueError):
        build_overpass_query({"clauses": [[condition]]}, LAHORE)


def test_parse_elements_maps_tags_to_a_raw_business():
    elements = [
        {
            "type": "node", "id": 1, "lat": 31.52, "lon": 74.35,
            "tags": {
                "name": "Rewatt Solar Energy", "shop": "electrical",
                "phone": "+923236444660", "contact:phone": "042 3577 1769",
                "website": "https://rewatt.pk", "email": "info@rewatt.pk",
                "addr:street": "Mall Road", "addr:city": "Lahore",
            },
        },
        {"type": "way", "id": 2, "center": {"lat": 31.6, "lon": 74.4}, "tags": {"name": "Bilal Traders", "shop": "trade"}},
        {"type": "node", "id": 3, "lat": 1, "lon": 1, "tags": {"shop": "electrical"}},
    ]

    first, second = parse_elements(elements)

    assert (first.source_key, first.external_id) == ("osm", "node/1")
    assert first.phones == ["+923236444660", "042 3577 1769"]
    assert first.emails == ["info@rewatt.pk"] and first.website == "https://rewatt.pk"
    assert first.address == "Mall Road, Lahore"
    assert first.categories == ["shop=electrical"]
    assert (first.latitude, first.longitude) == (31.52, 74.35)
    assert (second.external_id, second.latitude, second.longitude) == ("way/2", 31.6, 74.4)
    assert second.phones == [] and second.address is None


def test_search_posts_query_and_returns_businesses():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"elements": [
            {"type": "node", "id": 9, "lat": 1.0, "lon": 2.0, "tags": {"name": "Solar Hub"}},
        ]})

    result = make_source(handler).search(SearchQuery("solar dealer", LAHORE, osm_filter=FILTER))

    assert "nwr%5B%22shop%22%3D%22electrical%22%5D" in seen["body"]
    assert [b.name for b in result.businesses] == ["Solar Hub"]
    assert result.requests_made == 1


def test_search_without_osm_filter_makes_no_request():
    def handler(request):
        raise AssertionError("no request expected")

    result = make_source(handler).search(SearchQuery("solar ki dukan", LAHORE, language="ur-roman"))
    assert result.businesses == [] and result.requests_made == 0


def test_retries_rate_limits_then_succeeds_with_backoff():
    calls = []
    sleeps: list[float] = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429)
        return httpx.Response(200, json={"elements": []})

    make_source(handler, sleeps).search(SearchQuery("x", LAHORE, osm_filter=FILTER))

    assert len(calls) == 3
    assert sleeps == [3.0, 8.0]


def test_gives_up_after_retries_with_a_clear_error():
    def always_429(request):
        return httpx.Response(429)

    with pytest.raises(SourceRateLimitError):
        make_source(always_429).search(SearchQuery("x", LAHORE, osm_filter=FILTER))

    def always_504(request):
        return httpx.Response(504)

    with pytest.raises(SourceUnavailableError):
        make_source(always_504).search(SearchQuery("x", LAHORE, osm_filter=FILTER))


def test_runtime_error_remark_with_no_elements_is_a_failure_not_an_empty_result():
    def handler(request):
        return httpx.Response(200, json={"elements": [], "remark": "runtime error: Query timed out in \"query\""})

    with pytest.raises(SourceUnavailableError):
        make_source(handler).search(SearchQuery("x", LAHORE, osm_filter=FILTER))


def test_partial_results_with_a_remark_are_kept():
    def handler(request):
        return httpx.Response(200, json={
            "remark": "runtime error: Query timed out",
            "elements": [{"type": "node", "id": 1, "lat": 1, "lon": 1, "tags": {"name": "Kept"}}],
        })

    result = make_source(handler).search(SearchQuery("x", LAHORE, osm_filter=FILTER))
    assert [b.name for b in result.businesses] == ["Kept"]


def test_enforces_minimum_gap_between_requests():
    sleeps: list[float] = []
    now = [100.0]

    def handler(request):
        return httpx.Response(200, json={"elements": []})

    source = make_source(handler, sleeps, clock=lambda: now[0], min_interval=3.0)
    query = SearchQuery("x", LAHORE, osm_filter=FILTER)

    source.search(query)
    assert sleeps == []
    now[0] += 1.0
    source.search(query)
    assert sleeps == [pytest.approx(2.0)]
    now[0] += 10.0
    source.search(query)
    assert len(sleeps) == 1


def test_test_connection_reports_success_and_failure():
    ok, message = make_source(lambda r: httpx.Response(200, json={"elements": []})).test_connection()
    assert ok is True and "reachable" in message

    ok, message = make_source(lambda r: httpx.Response(503)).test_connection()
    assert ok is False and message


def test_request_with_retries_retries_network_errors():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ConnectTimeout("slow")
        return httpx.Response(200)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    response = request_with_retries(client, "GET", "https://x.test", sleep=lambda s: None)
    assert response.status_code == 200 and len(attempts) == 2


def test_retry_after_header_is_respected_up_to_a_cap():
    sleeps: list[float] = []
    responses = iter([httpx.Response(429, headers={"Retry-After": "5"}), httpx.Response(200)])
    client = httpx.Client(transport=httpx.MockTransport(lambda r: next(responses)))
    request_with_retries(client, "GET", "https://x.test", sleep=sleeps.append)
    assert sleeps == [5.0]


@pytest.mark.parametrize("status", [403, 406])
def test_a_refused_identification_is_explained_and_not_retried(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    source = make_source(handler)
    with pytest.raises(SourceAuthError, match="SCOUT_CONTACT_EMAIL"):
        source.search(SearchQuery(text="solar", area=LAHORE, language="en", osm_filter=FILTER))

    assert len(calls) == 1
