import time
from collections.abc import Callable
from http import HTTPStatus
from urllib.parse import quote

import httpx

from app.core.scouting.sources.base import (
    KIND_DISCOVERY,
    SourceAuthError,
    SourceBuildContext,
    SourceError,
    SourceInfo,
    request_with_retries,
)
from app.core.scouting.types import RawBusiness, SearchQuery, SearchResult

SOURCE_KEY = "tomtom"
ENDPOINT = "https://api.tomtom.com/search/2/poiSearch/{query}.json"
PAGE_SIZE = 100
MAX_PAGES = 3
REQUEST_TIMEOUT_SECONDS = 30
SEARCH_SECONDS = 1
RESULT_TYPE_POI = "POI"
TEST_QUERY = "solar"
TERMS_NOTE = (
    "TomTom's Maps API terms restrict storing or caching search results (section 12), and free developer plans "
    "generally give no long-term storage rights. Check the terms and your plan before you keep these leads."
)
KEY_REJECTED_MESSAGE = "TomTom rejected the API key or its permissions"
UNREADABLE_MESSAGE = "TomTom returned an unreadable response"


def parse_results(results: list[dict]) -> list[RawBusiness]:
    businesses: list[RawBusiness] = []
    for result in results:
        poi = result.get("poi") or {}
        name = (poi.get("name") or "").strip()
        if result.get("type") != RESULT_TYPE_POI or not name or not result.get("id"):
            continue

        position = result.get("position") or {}
        phone = (poi.get("phone") or "").strip()
        businesses.append(
            RawBusiness(
                source_key=SOURCE_KEY,
                external_id=result["id"],
                name=name,
                address=(result.get("address") or {}).get("freeformAddress"),
                latitude=position.get("lat"),
                longitude=position.get("lon"),
                phones=[phone] if phone else [],
                website=(poi.get("url") or "").strip() or None,
                categories=list(poi.get("categories") or []),
                raw=result,
            )
        )
    return businesses


class TomTomSource:
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
        south, west, north, east = query.area.rectangle
        area = {"topLeft": f"{north},{west}", "btmRight": f"{south},{east}"}

        businesses: list[RawBusiness] = []
        requests_made = 0
        truncated = False
        offset = 0

        for _ in range(MAX_PAGES):
            if max_requests is not None and requests_made >= max_requests:
                truncated = True
                break

            data = self._get(query.text, {**area, "limit": PAGE_SIZE, "ofs": offset})
            requests_made += 1
            results = data.get("results", [])
            businesses.extend(parse_results(results))

            offset += len(results)
            if len(results) < PAGE_SIZE or offset >= (data.get("summary") or {}).get("totalResults", 0):
                break

        return SearchResult(businesses=businesses, requests_made=requests_made, truncated=truncated)

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._get(TEST_QUERY, {"limit": 1})
        except SourceError as exc:
            return False, str(exc)
        return True, "TomTom API key works"

    def _get(self, text: str, params: dict) -> dict:
        url = ENDPOINT.format(query=quote(text, safe=""))
        response = request_with_retries(self._client, "GET", url, sleep=self._sleep, params={**params, "key": self._api_key})
        if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise SourceAuthError(_error_message(response, KEY_REJECTED_MESSAGE))
        if response.status_code != HTTPStatus.OK:
            raise SourceError(_error_message(response, f"TomTom returned HTTP {response.status_code}"))
        try:
            return response.json()
        except ValueError:
            raise SourceError(UNREADABLE_MESSAGE) from None


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        body = response.json()
    except ValueError:
        return fallback
    if not isinstance(body, dict):
        return fallback
    detail = body.get("errorText") or (body.get("detailedError") or {}).get("message")
    return f"{fallback}: {detail}" if detail else fallback


def build(context: SourceBuildContext) -> TomTomSource:
    if not context.api_key:
        raise ValueError("TomTom needs an API key")
    return TomTomSource(context.api_key)


INFO = SourceInfo(
    key=SOURCE_KEY,
    name="TomTom Places",
    description="Commercial place search with phones and websites. Needs an API key; billed per request after your free allowance.",
    kind=KIND_DISCOVERY,
    requires_api_key=True,
    default_enabled=False,
    is_paid=True,
    api_key_setting="TOMTOM_API_KEY",
    build=build,
    max_requests_per_search=MAX_PAGES,
    cost_per_request_setting="TOMTOM_COST_PER_REQUEST_USD",
    seconds_per_search=lambda settings: SEARCH_SECONDS,
    terms_note=TERMS_NOTE,
)
