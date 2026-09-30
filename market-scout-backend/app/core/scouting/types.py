"""Plain data types passed between sources, the engine and the persistence layer.

The engine knows nothing about the database or HTTP framework; everything crosses its
boundary as one of these.
"""
import math
from dataclasses import dataclass, field
from typing import Any

_KM_PER_DEGREE_LATITUDE = 111.32


@dataclass(frozen=True)
class SearchArea:
    latitude: float
    longitude: float
    radius_km: float
    name: str = ""
    # (south, west, north, east); when set it is used instead of the radius.
    bbox: tuple[float, float, float, float] | None = None

    @property
    def rectangle(self) -> tuple[float, float, float, float]:
        """(south, west, north, east): the explicit bbox, else the square around the centre.

        Both sources search a rectangle. Overpass in particular answers a bounding box in
        seconds but times out on the equivalent radius query ("around"), so a radius is
        turned into the square that contains it.
        """
        if self.bbox:
            return self.bbox
        d_lat = self.radius_km / _KM_PER_DEGREE_LATITUDE
        # A degree of longitude is shorter away from the equator.
        d_lng = self.radius_km / (_KM_PER_DEGREE_LATITUDE * max(math.cos(math.radians(self.latitude)), 0.01))
        return (
            self.latitude - d_lat,
            self.longitude - d_lng,
            self.latitude + d_lat,
            self.longitude + d_lng,
        )


@dataclass(frozen=True)
class SearchQuery:
    text: str
    area: SearchArea
    language: str = "en"
    # {"clauses": [["shop=electrical", "name~solar"], ...]} -- used by OpenStreetMap only.
    osm_filter: dict[str, Any] | None = None


@dataclass
class RawBusiness:
    """One business as reported by one source, before normalisation."""

    source_key: str
    external_id: str
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    # Raw strings; a single entry may hold several numbers ("0300-1, 0301-2").
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    website: str | None = None
    categories: list[str] = field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    businesses: list[RawBusiness]
    requests_made: int = 1
    # True when the source stopped early (e.g. the request budget ran out).
    truncated: bool = False
