import re
import time
from collections.abc import Callable
from http import HTTPStatus

import httpx

from app.core.constants import CONDITION_OPERATOR_EQUALS
from app.core.scouting.sources.base import (
    SourceAuthError,
    SourceError,
    SourceUnavailableError,
    request_with_retries,
)
from app.core.scouting.types import RawBusiness, SearchArea, SearchQuery, SearchResult

QUERY_TIMEOUT_SECONDS = 60
RESULT_LIMIT = 1000
DEFAULT_MIN_INTERVAL_SECONDS = 3.0
REQUEST_TIMEOUT_SECONDS = 90


SOURCE_KEY = "osm"

_CONDITION = re.compile(r"^([A-Za-z0-9_:]+)(=|~)(.+)$")
_UNSAFE_VALUE = re.compile(r'["\\;\[\]\r\n{}]')

_PHONE_TAGS = ("phone", "contact:phone", "mobile", "contact:mobile", "contact:whatsapp", "whatsapp")
_WEBSITE_TAGS = ("website", "contact:website", "url")
_EMAIL_TAGS = ("email", "contact:email")
_CATEGORY_TAGS = ("shop", "craft", "office", "amenity")
_ADDRESS_TAGS = ("addr:housenumber", "addr:street", "addr:suburb", "addr:city")


def _condition_to_ql(condition: str) -> str:
    match = _CONDITION.match(condition.strip())
    if not match:
        raise ValueError(f"Bad OSM condition: {condition!r}")
    key, operator, value = match.groups()
    if _UNSAFE_VALUE.search(value):
        raise ValueError(f"Unsafe characters in OSM condition: {condition!r}")
    if operator == CONDITION_OPERATOR_EQUALS:
        return f'["{key}"="{value}"]'
    return f'["{key}"~"{value}",i]'


def _area_to_ql(area: SearchArea) -> str:
    south, west, north, east = area.rectangle
    return f"({south:.5f},{west:.5f},{north:.5f},{east:.5f})"


def build_overpass_query(osm_filter: dict, area: SearchArea, timeout_s: int = QUERY_TIMEOUT_SECONDS, limit: int = RESULT_LIMIT) -> str:
    statements = []
    for clause in osm_filter["clauses"]:
        conditions = "".join(_condition_to_ql(condition) for condition in clause)
        statements.append(f"  nwr{conditions}{_area_to_ql(area)};")
    body = "\n".join(statements)
    return f"[out:json][timeout:{timeout_s}];\n(\n{body}\n);\nout center tags {limit};"


def parse_elements(elements: list[dict]) -> list[RawBusiness]:
    businesses: list[RawBusiness] = []
    for element in elements:
        tags = element.get("tags") or {}
        name = (tags.get("name") or tags.get("name:en") or "").strip()
        if not name:
            continue

        center = element.get("center") or {}
        latitude = element.get("lat", center.get("lat"))
        longitude = element.get("lon", center.get("lon"))

        address_parts = [tags[key] for key in _ADDRESS_TAGS if tags.get(key)]
        businesses.append(
            RawBusiness(
                source_key=SOURCE_KEY,
                external_id=f"{element['type']}/{element['id']}",
                name=name,
                address=", ".join(address_parts) or None,
                latitude=latitude,
                longitude=longitude,
                phones=[tags[key] for key in _PHONE_TAGS if tags.get(key)],
                emails=[tags[key] for key in _EMAIL_TAGS if tags.get(key)],
                website=next((tags[key] for key in _WEBSITE_TAGS if tags.get(key)), None)
                or tags.get("contact:facebook") or tags.get("facebook") or tags.get("contact:instagram"),
                categories=[f"{key}={tags[key]}" for key in _CATEGORY_TAGS if tags.get(key)],
                raw={"tags": tags},
            )
        )
    return businesses


class OsmSource:
    key = SOURCE_KEY

    def __init__(
        self,
        endpoint: str,
        user_agent: str,
        min_interval_s: float = DEFAULT_MIN_INTERVAL_SECONDS,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._endpoint = endpoint
        self._min_interval_s = min_interval_s
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": user_agent})
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None

    def search(self, query: SearchQuery, max_requests: int | None = None) -> SearchResult:
        if not query.osm_filter:
            return SearchResult(businesses=[], requests_made=0)

        ql = build_overpass_query(query.osm_filter, query.area)
        data = self._post(ql)

        elements = data.get("elements", [])
        remark = data.get("remark", "")
        if remark and re.search(r"timed out|out of memory|runtime error", remark, re.IGNORECASE) and not elements:
            raise SourceUnavailableError(f"Overpass gave up: {remark}")

        return SearchResult(businesses=parse_elements(elements), requests_made=1)

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._post("[out:json][timeout:10];node(1);out ids;")
        except SourceError as exc:
            return False, str(exc)
        return True, "Overpass API reachable"

    def _post(self, ql: str) -> dict:
        self._respect_min_interval()
        response = request_with_retries(
            self._client, "POST", self._endpoint, sleep=self._sleep, data={"data": ql}
        )
        self._last_request_at = self._clock()
        if response.status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.NOT_ACCEPTABLE):
            raise SourceAuthError(
                f"Overpass refused this app's identification (HTTP {response.status_code}). Set SCOUT_CONTACT_EMAIL to a "
                "real address you read (not a placeholder such as you@example.com), or leave it blank."
            )
        if response.status_code != HTTPStatus.OK:
            raise SourceError(f"Overpass returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise SourceUnavailableError("Overpass returned an unreadable response") from None

    def _respect_min_interval(self) -> None:
        if self._last_request_at is None:
            return
        wait = self._min_interval_s - (self._clock() - self._last_request_at)
        if wait > 0:
            self._sleep(wait)
