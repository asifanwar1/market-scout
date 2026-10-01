import json

import httpx
import pytest

from app.core.scouting.sources.base import SourceAuthError, SourceError, SourceRateLimitError
from app.core.scouting.sources.google_places import GooglePlacesSource, area_to_rectangle, parse_places
from app.core.scouting.types import SearchArea, SearchQuery

LAHORE = SearchArea(latitude=31.5204, longitude=74.3587, radius_km=20, name="Lahore")
QUERY = SearchQuery("solar panel dealer", LAHORE)


def place(n: int, **overrides) -> dict:
    data = {
        "id": f"place-{n}",
        "displayName": {"text": f"Solar Shop {n}"},
        "formattedAddress": f"Shop {n}, Mall Road, Lahore",
        "location": {"latitude": 31.5 + n / 1000, "longitude": 74.3},
        "internationalPhoneNumber": f"+92 300 000 000{n}",
        "websiteUri": f"https://shop{n}.pk",
        "rating": 4.5,
        "userRatingCount": 12,
        "primaryType": "electronics_store",
        "types": ["electronics_store", "store"],
        "businessStatus": "OPERATIONAL",
    }
    data.update(overrides)
    return data


def make_source(handler, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return GooglePlacesSource(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleeps.append,
    )


def test_rectangle_from_radius_is_centred_and_scaled():
    rect = area_to_rectangle(LAHORE)
    assert rect["low"]["latitude"] < 31.5204 < rect["high"]["latitude"]
    assert rect["high"]["latitude"] - rect["low"]["latitude"] == pytest.approx(2 * 20 / 111.32)
    assert (rect["high"]["longitude"] - rect["low"]["longitude"]) > (rect["high"]["latitude"] - rect["low"]["latitude"])

    bbox = area_to_rectangle(SearchArea(0, 0, 1, bbox=(1.0, 2.0, 3.0, 4.0)))
    assert bbox == {"low": {"latitude": 1.0, "longitude": 2.0}, "high": {"latitude": 3.0, "longitude": 4.0}}


def test_parse_places_maps_fields_and_skips_closed_or_nameless():
    places = [
        place(1),
        place(2, businessStatus="CLOSED_PERMANENTLY"),
        place(3, displayName={}),
        place(4, internationalPhoneNumber=None, nationalPhoneNumber="0300 1234567"),
    ]
    first, fourth = parse_places(places)

    assert (first.source_key, first.external_id, first.name) == ("google_places", "place-1", "Solar Shop 1")
    assert first.phones == ["+92 300 000 0001"]
    assert first.website == "https://shop1.pk"
    assert (first.rating, first.review_count) == (4.5, 12)
    assert first.categories == ["electronics_store", "store"]
    assert fourth.phones == ["0300 1234567"]


def test_search_sends_key_field_mask_and_restriction():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"places": [place(1)]})

    result = make_source(handler).search(QUERY)

    assert seen["headers"]["X-Goog-Api-Key"] == "test-key"
    assert "places.nationalPhoneNumber" in seen["headers"]["X-Goog-FieldMask"]
    assert seen["body"]["textQuery"] == "solar panel dealer in Lahore"
    assert seen["body"]["regionCode"] == "PK"
    assert set(seen["body"]["locationRestriction"]["rectangle"]) == {"low", "high"}
    assert [b.name for b in result.businesses] == ["Solar Shop 1"]
    assert result.requests_made == 1 and result.truncated is False


def test_follows_pagination_up_to_three_pages():
    tokens = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        tokens.append(body.get("pageToken"))
        page = len(tokens)
        return httpx.Response(200, json={"places": [place(page)], "nextPageToken": f"token-{page}"})

    result = make_source(handler).search(QUERY)

    assert tokens == [None, "token-1", "token-2"]
    assert len(result.businesses) == 3
    assert result.requests_made == 3


def test_request_budget_stops_pagination_and_flags_truncation():
    def handler(request):
        return httpx.Response(200, json={"places": [place(1)], "nextPageToken": "more"})

    result = make_source(handler).search(QUERY, max_requests=2)
    assert result.requests_made == 2 and result.truncated is True

    none_left = make_source(handler).search(QUERY, max_requests=0)
    assert none_left.requests_made == 0 and none_left.truncated is True and none_left.businesses == []


def test_budget_that_exactly_covers_the_results_is_not_truncated():
    def handler(request):
        return httpx.Response(200, json={"places": [place(1)]})

    result = make_source(handler).search(QUERY, max_requests=1)
    assert result.requests_made == 1 and result.truncated is False


def test_invalid_key_raises_auth_error_without_retrying():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(403, json={"error": {"message": "API key not valid"}})

    with pytest.raises(SourceAuthError, match="API key not valid"):
        make_source(handler).search(QUERY)
    assert len(calls) == 1


def test_other_client_errors_are_source_errors_and_rate_limits_retry():
    with pytest.raises(SourceError, match="HTTP 400"):
        make_source(lambda r: httpx.Response(400)).search(QUERY)

    sleeps: list[float] = []
    with pytest.raises(SourceRateLimitError):
        make_source(lambda r: httpx.Response(429), sleeps).search(QUERY)
    assert len(sleeps) == 3


def test_test_connection_uses_the_cheap_ids_only_mask():
    seen = {}

    def handler(request):
        seen["mask"] = request.headers["X-Goog-FieldMask"]
        return httpx.Response(200, json={"places": []})

    ok, message = make_source(handler).test_connection()
    assert ok is True and seen["mask"] == "places.id"

    ok, message = make_source(lambda r: httpx.Response(403, json={"error": {"message": "bad key"}})).test_connection()
    assert ok is False and "bad key" in message
