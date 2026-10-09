import httpx
import pytest

from app.core.scouting.sources import here
from app.core.scouting.sources.base import SourceAuthError, SourceError, SourceRateLimitError
from app.core.scouting.types import SearchArea, SearchQuery

LAHORE = SearchArea(latitude=31.5204, longitude=74.3587, radius_km=20, name="Lahore")
QUERY = SearchQuery("solar panel dealer", LAHORE)


def item(n: int, **overrides) -> dict:
    data = {
        "title": f"Solar Shop {n}",
        "id": f"here:pds:place:{n}",
        "resultType": "place",
        "address": {
            "label": f"Solar Shop {n}, {n} Mall Road, Gulberg, Lahore, Pakistan",
            "houseNumber": str(n),
            "street": "Mall Road",
            "district": "Gulberg",
            "city": "Lahore",
        },
        "position": {"lat": 31.5 + n / 1000, "lng": 74.3},
        "categories": [{"id": "600-6000", "name": "Store", "primary": False}, {"id": "600-6900", "name": "Electronics Shop", "primary": True}],
        "contacts": [
            {
                "phone": [{"value": f"+9242355000{n}"}, {"value": "+924235999999"}],
                "mobile": [{"value": f"+92300000000{n}"}],
                "www": [{"value": f"https://shop{n}.pk"}],
                "email": [{"value": f"info@shop{n}.pk"}],
            }
        ],
    }
    data.update(overrides)
    return data


def make_source(handler, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return here.HereSource(api_key="test-key", client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=sleeps.append)


def test_parse_items_maps_fields_and_skips_non_places_and_nameless_items():
    items = [
        item(1),
        item(2, resultType="street"),
        item(3, title=""),
        item(4, id=None),
        item(5, contacts=[], categories=None, address={"label": "Only a label"}),
    ]
    first, fifth = here.parse_items(items)

    assert (first.source_key, first.external_id, first.name) == ("here", "here:pds:place:1", "Solar Shop 1")
    assert first.address == "1 Mall Road, Gulberg, Lahore"
    assert (first.latitude, first.longitude) == (31.501, 74.3)
    assert first.phones == ["+92423550001", "+924235999999", "+923000000001"]
    assert first.emails == ["info@shop1.pk"] and first.website == "https://shop1.pk"
    assert first.categories == ["Electronics Shop", "Store"]
    assert first.raw["id"] == "here:pds:place:1"
    assert fifth.phones == [] and fifth.website is None and fifth.categories == [] and fifth.address == "Only a label"


def test_search_sends_the_key_the_query_and_the_area_as_a_bounding_box():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = request.url
        return httpx.Response(200, json={"items": [item(1)]})

    result = make_source(handler).search(QUERY)

    params = seen["url"].params
    assert seen["url"].host == "discover.search.hereapi.com" and seen["url"].path == "/v1/discover"
    assert params["apiKey"] == "test-key" and params["q"] == "solar panel dealer" and params["limit"] == "100"
    west, south, east, north = (float(part) for part in params["in"].removeprefix("bbox:").split(","))
    assert south < 31.5204 < north and west < 74.3587 < east
    assert [business.external_id for business in result.businesses] == ["here:pds:place:1"]
    assert result.requests_made == 1 and result.truncated is False


def test_a_request_budget_of_zero_makes_no_request():
    calls = []
    result = make_source(lambda request: calls.append(request) or httpx.Response(200, json={"items": []})).search(QUERY, max_requests=0)

    assert calls == [] and result.requests_made == 0 and result.truncated is True


def test_a_rejected_key_raises_an_auth_error_without_retrying_and_never_shows_the_key():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(401, json={"error": "Unauthorized", "error_description": "apiKey invalid. apiKey not found."})

    with pytest.raises(SourceAuthError, match="apiKey invalid") as raised:
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

    with pytest.raises(SourceError, match="HTTP 400: Invalid bbox"):
        make_source(lambda request: httpx.Response(400, json={"title": "Invalid bbox"})).search(QUERY)


def test_an_unreadable_answer_is_a_source_error():
    with pytest.raises(SourceError, match="unreadable"):
        make_source(lambda request: httpx.Response(200, content=b"not json")).search(QUERY)


def test_test_connection_asks_for_one_result_and_reports_the_outcome():
    seen = {}

    def ok(request: httpx.Request) -> httpx.Response:
        seen["params"] = request.url.params
        return httpx.Response(200, json={"items": []})

    assert make_source(ok).test_connection() == (True, "HERE API key works")
    assert seen["params"]["limit"] == "1" and "at" in seen["params"]

    good, message = make_source(lambda request: httpx.Response(403, json={"error": "Forbidden"})).test_connection()
    assert good is False and "rejected the API key" in message


def test_a_source_cannot_be_built_without_a_key():
    context = here.SourceBuildContext(api_key=None, user_agent="x", settings=None)
    with pytest.raises(ValueError, match="API key"):
        here.build(context)
