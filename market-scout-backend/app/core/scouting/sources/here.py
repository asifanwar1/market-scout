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
from app.core.scouting.types import RawBusiness, SearchQuery, SearchResult

SOURCE_KEY = "here"
ENDPOINT = "https://discover.search.hereapi.com/v1/discover"
PAGE_SIZE = 100
REQUEST_TIMEOUT_SECONDS = 30
SEARCH_SECONDS = 1
RESULT_TYPE_PLACE = "place"
TEST_QUERY = "solar"
TEST_CENTER = "31.5204,74.3587"
TERMS_NOTE = (
    "HERE's platform terms (section 6.3e) limit keeping its results outside the HERE platform to 30 days, "
    "unless they are used only for internal testing or evaluation. Check your plan before you keep these leads."
)
KEY_REJECTED_MESSAGE = "HERE rejected the API key or its permissions"
UNREADABLE_MESSAGE = "HERE returned an unreadable response"

PHONE_FIELDS = ("phone", "mobile")
WEBSITE_FIELD = "www"
EMAIL_FIELD = "email"


def _contact_values(contacts: list[dict], field: str) -> list[str]:
    values = [entry.get("value", "").strip() for contact in contacts for entry in contact.get(field, [])]
    return list(dict.fromkeys(value for value in values if value))


def _address(address: dict) -> str | None:
    street = " ".join(part for part in (address.get("houseNumber"), address.get("street")) if part)
    parts = list(dict.fromkeys(part for part in (street, address.get("district"), address.get("city")) if part))
    return ", ".join(parts) if parts else address.get("label")


def _categories(item: dict) -> list[str]:
    categories = sorted(item.get("categories") or [], key=lambda category: not category.get("primary", False))
    return [category["name"] for category in categories if category.get("name")]


def parse_items(items: list[dict]) -> list[RawBusiness]:
    businesses: list[RawBusiness] = []
    for item in items:
        if item.get("resultType") != RESULT_TYPE_PLACE:
            continue
        name = (item.get("title") or "").strip()
        if not name or not item.get("id"):
            continue

        position = item.get("position") or {}
        contacts = item.get("contacts") or []
        phones = list(dict.fromkeys(value for field in PHONE_FIELDS for value in _contact_values(contacts, field)))
        websites = _contact_values(contacts, WEBSITE_FIELD)

        businesses.append(
            RawBusiness(
                source_key=SOURCE_KEY,
                external_id=item["id"],
                name=name,
                address=_address(item.get("address") or {}),
                latitude=position.get("lat"),
                longitude=position.get("lng"),
                phones=phones,
                emails=_contact_values(contacts, EMAIL_FIELD),
                website=websites[0] if websites else None,
                categories=_categories(item),
                raw=item,
            )
        )
    return businesses


class HereSource:
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
        if max_requests is not None and max_requests < 1:
            return SearchResult(businesses=[], requests_made=0, truncated=True)

        south, west, north, east = query.area.rectangle
        data = self._get({"q": query.text, "in": f"bbox:{west},{south},{east},{north}", "limit": PAGE_SIZE})
        return SearchResult(businesses=parse_items(data.get("items", [])), requests_made=1)

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._get({"q": TEST_QUERY, "at": TEST_CENTER, "limit": 1})
        except SourceError as exc:
            return False, str(exc)
        return True, "HERE API key works"

    def _get(self, params: dict) -> dict:
        response = request_with_retries(self._client, "GET", ENDPOINT, sleep=self._sleep, params={**params, "apiKey": self._api_key})
        if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise SourceAuthError(_error_message(response, KEY_REJECTED_MESSAGE))
        if response.status_code != HTTPStatus.OK:
            raise SourceError(_error_message(response, f"HERE returned HTTP {response.status_code}"))
        try:
            return response.json()
        except ValueError:
            raise SourceError(UNREADABLE_MESSAGE) from None


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        body = response.json()
    except ValueError:
        return fallback
    detail = body.get("error_description") or body.get("cause") or body.get("title") if isinstance(body, dict) else None
    return f"{fallback}: {detail}" if detail else fallback


def build(context: SourceBuildContext) -> HereSource:
    if not context.api_key:
        raise ValueError("HERE needs an API key")
    return HereSource(context.api_key)


INFO = SourceInfo(
    key=SOURCE_KEY,
    name="HERE Places",
    description="Commercial place search with phones and websites. Needs an API key; billed per request after your free allowance.",
    kind=KIND_DISCOVERY,
    requires_api_key=True,
    default_enabled=False,
    is_paid=True,
    api_key_setting="HERE_API_KEY",
    build=build,
    max_requests_per_search=1,
    cost_per_request_setting="HERE_COST_PER_REQUEST_USD",
    seconds_per_search=lambda settings: SEARCH_SECONDS,
    terms_note=TERMS_NOTE,
)
