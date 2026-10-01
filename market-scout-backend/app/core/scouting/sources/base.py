import time
from collections.abc import Callable
from http import HTTPStatus
from typing import Protocol

import httpx

from app.core.scouting.types import SearchQuery, SearchResult

MAX_RETRY_AFTER_SECONDS = 60.0


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DEFAULT_RETRY_DELAYS = (3.0, 8.0, 20.0)


class SourceError(Exception):
    pass


class SourceAuthError(SourceError):
    pass


class SourceRateLimitError(SourceError):
    pass


class SourceUnavailableError(SourceError):
    pass


class Source(Protocol):
    key: str

    def search(self, query: SearchQuery, max_requests: int | None = None) -> SearchResult:
        pass

    def test_connection(self) -> tuple[bool, str]:
        pass


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
    **kwargs,
) -> httpx.Response:
    last_problem: SourceError | None = None

    for attempt in range(len(retry_delays) + 1):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            last_problem = SourceUnavailableError(f"Network problem: {exc.__class__.__name__}")
            delay = None
        else:
            if response.status_code not in RETRYABLE_STATUS:
                return response
            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                last_problem = SourceRateLimitError("Rate limited (HTTP 429)")
            else:
                last_problem = SourceUnavailableError(f"Server error (HTTP {response.status_code})")
            delay = _retry_after_seconds(response)

        if attempt < len(retry_delays):
            sleep(delay if delay is not None else retry_delays[attempt])

    assert last_problem is not None
    raise last_problem


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After", "")
    if value.isdigit():
        return min(float(value), MAX_RETRY_AFTER_SECONDS)
    return None
