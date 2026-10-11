from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.features.runs.models import RunStatus, TaskStatus

CITIES_MAX = 100
SOURCES_MAX = 5
SEGMENTS_MAX = 30
PAID_REQUESTS_MAX = 100_000



def dedupe_values(values: list) -> list:
    return list(dict.fromkeys(values))


class RunCreate(BaseModel):
    profile_id: int
    geography_ids: list[int] = Field(min_length=1, max_length=CITIES_MAX)
    source_keys: list[str] = Field(min_length=1, max_length=SOURCES_MAX)
    segment_slugs: Optional[list[str]] = Field(default=None, min_length=1, max_length=SEGMENTS_MAX)
    enrich_websites: bool = True
    refresh: bool = False
    max_paid_requests: Optional[int] = Field(default=None, ge=1, le=PAID_REQUESTS_MAX)

    @field_validator("geography_ids", "source_keys")
    @classmethod
    def dedupe_lists(cls, v: list) -> list:
        return dedupe_values(v)

    @field_validator("segment_slugs")
    @classmethod
    def dedupe_optional_list(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return dedupe_values(v) if v is not None else v


class SourceEstimate(BaseModel):
    source_key: str
    name: str
    is_paid: bool
    tasks: int
    tasks_skipped: int
    max_requests: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class RunEstimateResponse(BaseModel):
    profile_name: str
    cities: int
    tasks_total: int
    tasks_to_run: int
    tasks_skipped: int
    by_source: list[SourceEstimate]
    paid_requests_max: int
    estimated_cost_usd: float
    estimated_minutes: int
    allowed: bool
    warnings: list[str]


class RunResponse(BaseModel):
    id: int
    profile_id: Optional[int] = None
    profile_name: str
    created_by_id: Optional[int] = None
    schedule_id: Optional[int] = None
    schedule_name: Optional[str] = None
    status: RunStatus
    source_keys: list[str]
    segment_slugs: Optional[list[str]] = None
    enrich_websites: bool
    refresh: bool
    max_paid_requests: Optional[int] = None
    paid_requests_used: int
    estimated_cost_usd: float
    tasks_total: int
    tasks_done: int
    tasks_failed: int
    tasks_skipped: int
    progress_percent: int
    enrich_total: int
    enrich_done: int
    stats: dict[str, dict[str, Any]]
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    data: list[RunResponse]
    count: int


class RunTaskResponse(BaseModel):
    id: int
    source_key: str
    geography_id: Optional[int] = None
    geography_name: str
    term_text: str
    term_language: str
    segment_slug: str
    status: TaskStatus
    results_count: int
    new_count: int
    requests_made: int
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RunTaskListResponse(BaseModel):
    data: list[RunTaskResponse]
    count: int
