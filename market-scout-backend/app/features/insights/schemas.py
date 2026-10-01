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
    by_status: dict[str, int]


class CoverageSegment(BaseModel):
    slug: str
    name: str


class CoverageCity(BaseModel):
    geography_id: int
    city: str
    province: Optional[str] = None
    total: int
    counts: dict[str, int]


class CoverageResponse(BaseModel):
    segments: list[CoverageSegment]
    cities: list[CoverageCity]
    unplaced: int


class GapCity(BaseModel):
    geography_id: int
    city: str
    province: Optional[str] = None
    total: int
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
    kind: Literal["discovery", "enrichment", "import"]
    is_paid: bool
    found: int
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
    previous_seen_at: datetime
    latest_seen_at: datetime


class MoversResponse(BaseModel):
    days: int
    data: list[Mover]
    count: int
