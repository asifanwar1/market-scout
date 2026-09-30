import math
from dataclasses import dataclass, field

from rapidfuzz import fuzz

# Two records this close together *and* with near-identical names are one business.
GEO_MATCH_RADIUS_M = 150
GEO_NAME_SIMILARITY = 85
# A shared phone number is strong evidence, but a directory or market switchboard can
# be shared by unrelated shops, so the names must at least vaguely agree.
PHONE_NAME_SIMILARITY = 40


@dataclass(frozen=True)
class BusinessKeys:
    normalized_name: str
    phones: frozenset[str] = field(default_factory=frozenset)
    domain: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class MatchDecision:
    is_match: bool
    reason: str | None = None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def is_same_business(a: BusinessKeys, b: BusinessKeys) -> MatchDecision:
    """Decide whether two records describe one business. Order: domain, phone, location+name."""
    if a.domain and a.domain == b.domain:
        return MatchDecision(True, "website")

    if a.phones & b.phones and _name_similarity(a, b, fuzz.token_set_ratio) >= PHONE_NAME_SIMILARITY:
        return MatchDecision(True, "phone")

    if None not in (a.latitude, a.longitude, b.latitude, b.longitude):
        close = haversine_m(a.latitude, a.longitude, b.latitude, b.longitude) <= GEO_MATCH_RADIUS_M
        if close and _name_similarity(a, b, fuzz.token_sort_ratio) >= GEO_NAME_SIMILARITY:
            return MatchDecision(True, "location")

    return MatchDecision(False)


def _name_similarity(a: BusinessKeys, b: BusinessKeys, scorer) -> float:
    if not a.normalized_name or not b.normalized_name:
        return 0.0
    return scorer(a.normalized_name, b.normalized_name)
