import time
from collections.abc import Callable
from http import HTTPStatus

import httpx

from app.core.scouting.sources.base import (
    KIND_DISCOVERY,
    SourceAuthError,
    SourceBuildContext,
    SourceError,
    SourceInfo,
    request_with_retries,
)
from app.core.scouting.types import RawBusiness, SearchArea, SearchQuery, SearchResult

CLOSED_STATUSES = ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY")
REQUEST_TIMEOUT_SECONDS = 30


SOURCE_KEY = "google_places"
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
MAX_PAGES = 3
SEARCH_SECONDS = 3
TERMS_NOTE = (
    "Google's terms limit how long Places data may be stored. Check them before you keep these leads long term."
)
PAGE_SIZE = 20

_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.internationalPhoneNumber",
        "places.websiteUri",
        "places.rating",
        "places.userRatingCount",
        "places.googleMapsUri",
        "places.primaryType",
        "places.types",
        "places.businessStatus",
        "nextPageToken",
    ]
)


def area_to_rectangle(area: SearchArea) -> dict:
    south, west, north, east = area.rectangle
    return {
        "low": {"latitude": south, "longitude": west},
        "high": {"latitude": north, "longitude": east},
    }


def parse_places(places: list[dict]) -> list[RawBusiness]:
    businesses: list[RawBusiness] = []
    for place in places:
        if place.get("businessStatus") in CLOSED_STATUSES:
            continue
        name = ((place.get("displayName") or {}).get("text") or "").strip()
        if not name or not place.get("id"):
            continue

        location = place.get("location") or {}
        phone = place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber")
        categories = [place["primaryType"]] if place.get("primaryType") else []
        categories += [t for t in place.get("types", []) if t not in categories]

        businesses.append(
            RawBusiness(
                source_key=SOURCE_KEY,
                external_id=place["id"],
                name=name,
                address=place.get("formattedAddress"),
                latitude=location.get("latitude"),
                longitude=location.get("longitude"),
                phones=[phone] if phone else [],
                website=place.get("websiteUri"),
                categories=categories,
                rating=place.get("rating"),
                review_count=place.get("userRatingCount"),
                raw=place,
            )
        )
    return businesses


class GooglePlacesSource:
    key = SOURCE_KEY

    def __init__(
        self,
        api_key: str,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)
        self._sleep = sleep

    def search(self, query: SearchQuery, max_requests: int | None = None) -> SearchResult:
        text = f"{query.text} in {query.area.name}" if query.area.name else query.text
        body: dict = {
            "textQuery": text,
            "pageSize": PAGE_SIZE,
            "regionCode": "PK",
            "locationRestriction": {"rectangle": area_to_rectangle(query.area)},
        }

        businesses: list[RawBusiness] = []
        requests_made = 0
        truncated = False

        for _ in range(MAX_PAGES):
            if max_requests is not None and requests_made >= max_requests:
                truncated = True
                break

            data = self._post(body, _FIELD_MASK)
            requests_made += 1
            businesses.extend(parse_places(data.get("places", [])))

            next_token = data.get("nextPageToken")
            if not next_token:
                break
            body = {**body, "pageToken": next_token}

        return SearchResult(businesses=businesses, requests_made=requests_made, truncated=truncated)

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._post({"textQuery": "solar", "pageSize": 1, "regionCode": "PK"}, "places.id")
        except SourceError as exc:
            return False, str(exc)
        return True, "Google Places API key works"

    def _post(self, body: dict, field_mask: str) -> dict:
        response = request_with_retries(
            self._client,
            "POST",
            ENDPOINT,
            sleep=self._sleep,
            json=body,
            headers={"X-Goog-Api-Key": self._api_key, "X-Goog-FieldMask": field_mask},
        )
        if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise SourceAuthError(_error_message(response, "Google rejected the API key or its permissions"))
        if response.status_code != HTTPStatus.OK:
            raise SourceError(_error_message(response, f"Google Places returned HTTP {response.status_code}"))
        return response.json()


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        message = response.json().get("error", {}).get("message")
    except ValueError:
        message = None
    return f"{fallback}: {message}" if message else fallback


def build(context: SourceBuildContext) -> GooglePlacesSource:
    if not context.api_key:
        raise ValueError("Google Places needs an API key")
    return GooglePlacesSource(context.api_key)


INFO = SourceInfo(
    key=SOURCE_KEY,
    name="Google Places API",
    description="Best coverage of phone numbers and websites. Needs an API key and is billed per request.",
    kind=KIND_DISCOVERY,
    requires_api_key=True,
    default_enabled=False,
    is_paid=True,
    api_key_setting="GOOGLE_PLACES_API_KEY",
    build=build,
    max_requests_per_search=MAX_PAGES,
    cost_per_request_setting="PLACES_COST_PER_REQUEST_USD",
    seconds_per_search=lambda settings: SEARCH_SECONDS,
    terms_note=TERMS_NOTE,
)
