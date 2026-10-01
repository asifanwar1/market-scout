from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


class Bucket(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class OverviewResponse(BaseModel):
    total: int
    with_phone: int
    whatsapp_likely: int
    with_email: int
    with_website: int
    new_last_7_days: int
    new_last_30_days: int
    # lead status -> how many
    by_status: dict[str, int]


class CoverageSegment(BaseModel):
    slug: str
    name: str


class CoverageCity(BaseModel):
    geography_id: int
    city: str
    province: Optional[str] = None
    total: int
    # segment slug -> leads; "unclassified" holds leads with no segment
    counts: dict[str, int]


class CoverageResponse(BaseModel):
    segments: list[CoverageSegment]
    cities: list[CoverageCity]
    # Leads with no city recorded, so the matrix always adds up to the overview total.
    unplaced: int


class GapCity(BaseModel):
    geography_id: int
    city: str
    province: Optional[str] = None
    total: int
    # never_searched: no completed search here yet; few_found: searched but little turned up
    reason: Literal["never_searched", "few_found"]
    searches_done: int
    last_searched_at: Optional[datetime] = None
    missing_segments: list[str]


class GapsResponse(BaseModel):
    threshold: int
    data: list[GapCity]
    count: int


class TimelinePoint(BaseModel):
    period: str
    new: int
    total: int


class TimelineResponse(BaseModel):
    bucket: Bucket
    data: list[TimelinePoint]


class SourceQuality(BaseModel):
    key: str
    name: str
    kind: Literal["discovery", "enrichment"]
    is_paid: bool
    # Businesses this source reported (or, for website reading, added contacts to).
    found: int
    # Reported by this source and no other discovery source. None for website reading.
    exclusive: Optional[int] = None
    with_phone: int
    with_whatsapp: int
    with_email: int
    with_website: int
    requests: int
    estimated_cost_usd: Optional[float] = None
    cost_per_lead_usd: Optional[float] = None


class SourcesResponse(BaseModel):
    data: list[SourceQuality]
    count: int


class Mover(BaseModel):
    business_id: int
    name: str
    city: Optional[str] = None
    rating: Optional[float] = None
    review_count: int
    review_change: int
    # The search before the latest one, which the change is measured against.
    previous_seen_at: datetime
    latest_seen_at: datetime


class MoversResponse(BaseModel):
    days: int
    data: list[Mover]
    count: int
