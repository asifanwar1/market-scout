import time
from collections.abc import Callable
from typing import Protocol

import httpx

from app.core.scouting.types import SearchQuery, SearchResult

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DEFAULT_RETRY_DELAYS = (3.0, 8.0, 20.0)


class SourceError(Exception):
    """The source could not answer this search."""


class SourceAuthError(SourceError):
    """The key is missing, invalid or not allowed. Retrying will not help."""


class SourceRateLimitError(SourceError):
    """Still being throttled after all retries."""


class SourceUnavailableError(SourceError):
    """Server errors or timeouts persisted through all retries."""


class Source(Protocol):
    key: str

    def search(self, query: SearchQuery, max_requests: int | None = None) -> SearchResult:
        """Run one search. ``max_requests`` caps how many API calls this search may make."""

    def test_connection(self) -> tuple[bool, str]:
        """A cheap call that proves the source is reachable and the key (if any) works."""


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
    **kwargs,
) -> httpx.Response:
    """Send a request, retrying rate-limit / server errors / timeouts with backoff.

    Returns the first non-retryable response (the caller inspects 4xx). Raises
    SourceRateLimitError / SourceUnavailableError once the retries are used up.
    """
    last_problem: SourceError | None = None

    for attempt in range(len(retry_delays) + 1):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as exc:  # includes timeouts
            last_problem = SourceUnavailableError(f"Network problem: {exc.__class__.__name__}")
            delay = None
        else:
            if response.status_code not in RETRYABLE_STATUS:
                return response
            if response.status_code == 429:
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
        return min(float(value), 60.0)
    return None
