"""Google Places API (New) Text Search. Needs an API key; billed per request, so every
search reports how many requests it made and honours a request cap."""
import time
from typing import Callable

import httpx

from app.core.scouting.sources.base import (
    SourceAuthError, SourceError, request_with_retries,
)
from app.core.scouting.types import RawBusiness, SearchArea, SearchQuery, SearchResult

SOURCE_KEY = "google_places"
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
MAX_PAGES = 3  # the API returns at most 60 results (3 pages of 20) per query
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
    """Text Search can only hard-restrict to a rectangle."""
    south, west, north, east = area.rectangle
    return {
        "low": {"latitude": south, "longitude": west},
        "high": {"latitude": north, "longitude": east},
    }


def parse_places(places: list[dict]) -> list[RawBusiness]:
    businesses: list[RawBusiness] = []
    for place in places:
        if place.get("businessStatus") in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
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
        self._client = client or httpx.Client(timeout=30)
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
            # IDs-only field mask: the cheapest possible request that still validates the key.
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
        if response.status_code in (401, 403):
            raise SourceAuthError(_error_message(response, "Google rejected the API key or its permissions"))
        if response.status_code != 200:
            raise SourceError(_error_message(response, f"Google Places returned HTTP {response.status_code}"))
        return response.json()


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        message = response.json().get("error", {}).get("message")
    except ValueError:
        message = None
    return f"{fallback}: {message}" if message else fallback
