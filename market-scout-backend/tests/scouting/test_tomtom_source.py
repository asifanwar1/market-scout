import httpx
import pytest

from app.core.scouting.sources import tomtom
from app.core.scouting.sources.base import SourceAuthError, SourceError, SourceRateLimitError
from app.core.scouting.types import SearchArea, SearchQuery

LAHORE = SearchArea(latitude=31.5204, longitude=74.3587, radius_km=20, name="Lahore")
QUERY = SearchQuery("solar panel dealer", LAHORE)


def result(n: int, **overrides) -> dict:
    data = {
        "type": "POI",
        "id": f"tomtom-{n}",
        "score": 3.5,
        "poi": {
            "name": f"Solar Shop {n}",
            "phone": f"+92 42 3550 000{n}",
            "url": f"www.shop{n}.pk",
            "categories": ["shop", "electronics"],
            "categorySet": [{"id": 7373}],
        },
        "address": {"municipality": "Lahore", "countryCode": "PK", "freeformAddress": f"{n} Mall Road, Lahore"},
        "position": {"lat": 31.5 + n / 1000, "lon": 74.3},
    }
    data.update(overrides)
    return data


def page(first: int, count: int, total: int) -> dict:
    return {"summary": {"numResults": count, "offset": first - 1, "totalResults": total}, "results": [result(first + i) for i in range(count)]}


def make_source(handler, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return tomtom.TomTomSource(api_key="test-key", client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=sleeps.append)


def test_parse_results_maps_fields_and_skips_non_pois_and_nameless_results():
    results = [
        result(1),
        result(2, type="Street"),
        result(3, poi={"name": ""}),
        result(4, id=None),
        result(5, poi={"name": "Bare Shop"}, address=None),
    ]
    first, fifth = tomtom.parse_results(results)

    assert (first.source_key, first.external_id, first.name) == ("tomtom", "tomtom-1", "Solar Shop 1")
    assert first.phones == ["+92 42 3550 0001"] and first.website == "www.shop1.pk"
    assert first.address == "1 Mall Road, Lahore" and (first.latitude, first.longitude) == (31.501, 74.3)
    assert first.categories == ["shop", "electronics"] and first.raw["id"] == "tomtom-1"
    assert fifth.phones == [] and fifth.website is None and fifth.address is None and fifth.categories == []


def test_search_puts_the_query_in_the_path_and_the_area_in_a_bounding_box():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = request.url
        return httpx.Response(200, json=page(1, 1, 1))

    outcome = make_source(handler).search(QUERY)

    url = seen["url"]
    assert url.host == "api.tomtom.com" and url.raw_path.startswith(b"/search/2/poiSearch/solar%20panel%20dealer.json?")
    assert url.params["key"] == "test-key" and url.params["limit"] == "100" and url.params["ofs"] == "0"
    north, west = (float(part) for part in url.params["topLeft"].split(","))
    south, east = (float(part) for part in url.params["btmRight"].split(","))
    assert south < 31.5204 < north and west < 74.3587 < east
    assert [business.external_id for business in outcome.businesses] == ["tomtom-1"]
    assert outcome.requests_made == 1 and outcome.truncated is False


def test_a_slash_in_the_query_cannot_change_the_path():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["raw_path"] = request.url.raw_path
        return httpx.Response(200, json=page(1, 0, 0))

    make_source(handler).search(SearchQuery("solar/../admin?x=1", LAHORE))

    assert seen["raw_path"].startswith(b"/search/2/poiSearch/solar%2F..%2Fadmin%3Fx%3D1.json")


def test_it_follows_pages_by_offset_until_the_results_run_out():
    offsets = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["ofs"])
        offsets.append(offset)
        return httpx.Response(200, json=page(offset + 1, 100 if offset < 200 else 20, 220))

    outcome = make_source(handler).search(QUERY)

    assert offsets == [0, 100, 200] and len(outcome.businesses) == 220
    assert outcome.requests_made == 3 and outcome.truncated is False


def test_a_short_first_page_stops_after_one_request():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=page(1, 40, 40))

    assert make_source(handler).search(QUERY).requests_made == 1
    assert len(calls) == 1


def test_never_asks_for_more_than_three_pages():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=page(len(calls) * 100 - 99, 100, 1000))

    outcome = make_source(handler).search(QUERY)

    assert len(calls) == tomtom.MAX_PAGES == outcome.requests_made


def test_a_request_budget_stops_paging_and_flags_truncation():
    outcome = make_source(lambda request: httpx.Response(200, json=page(1, 100, 1000))).search(QUERY, max_requests=1)

    assert outcome.requests_made == 1 and outcome.truncated is True and len(outcome.businesses) == 100


def test_a_budget_that_exactly_covers_the_results_is_not_truncated():
    outcome = make_source(lambda request: httpx.Response(200, json=page(1, 10, 10))).search(QUERY, max_requests=1)

    assert outcome.truncated is False


def test_a_rejected_key_raises_an_auth_error_without_retrying_and_never_shows_the_key():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(403, json={"errorText": "Developer Inactive"})

    with pytest.raises(SourceAuthError, match="Developer Inactive") as raised:
        make_source(handler).search(QUERY)

    assert len(calls) == 1 and "test-key" not in str(raised.value)


def test_other_errors_are_source_errors_and_rate_limits_are_retried():
    sleeps = []
    calls = []

    def limited(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429)

    with pytest.raises(SourceRateLimitError):
        make_source(limited, sleeps).search(QUERY)
    assert len(calls) == 4 and len(sleeps) == 3

    with pytest.raises(SourceError, match="HTTP 400: bad box"):
        make_source(lambda request: httpx.Response(400, json={"detailedError": {"message": "bad box"}})).search(QUERY)


def test_an_unreadable_answer_is_a_source_error():
    with pytest.raises(SourceError, match="unreadable"):
        make_source(lambda request: httpx.Response(200, content=b"not json")).search(QUERY)


def test_test_connection_asks_for_one_result_and_reports_the_outcome():
    seen = {}

    def ok(request: httpx.Request) -> httpx.Response:
        seen["params"] = request.url.params
        return httpx.Response(200, json=page(1, 0, 0))

    assert make_source(ok).test_connection() == (True, "TomTom API key works")
    assert seen["params"]["limit"] == "1"

    good, message = make_source(lambda request: httpx.Response(403, json={"errorText": "Forbidden"})).test_connection()
    assert good is False and "rejected the API key" in message


def test_a_source_cannot_be_built_without_a_key():
    context = tomtom.SourceBuildContext(api_key=None, user_agent="x", settings=None)
    with pytest.raises(ValueError, match="API key"):
        tomtom.build(context)
