import math
from dataclasses import dataclass, field
from typing import Any

MIN_LONGITUDE_SCALE = 0.01


_KM_PER_DEGREE_LATITUDE = 111.32


@dataclass(frozen=True)
class SearchArea:
    latitude: float
    longitude: float
    radius_km: float
    name: str = ""
    bbox: tuple[float, float, float, float] | None = None

    @property
    def rectangle(self) -> tuple[float, float, float, float]:
        if self.bbox:
            return self.bbox
        d_lat = self.radius_km / _KM_PER_DEGREE_LATITUDE
        d_lng = self.radius_km / (_KM_PER_DEGREE_LATITUDE * max(math.cos(math.radians(self.latitude)), MIN_LONGITUDE_SCALE))
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
    osm_filter: dict[str, Any] | None = None


@dataclass
class RawBusiness:
    source_key: str
    external_id: str
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    website: str | None = None
    categories: list[str] = field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    unreliable_phones: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    businesses: list[RawBusiness]
    requests_made: int = 1
    truncated: bool = False
