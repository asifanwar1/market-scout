from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.features.runs.models import RunStatus, TaskStatus


def _dedupe(values: list) -> list:
    return list(dict.fromkeys(values))


class RunCreate(BaseModel):
    profile_id: int
    # Any level: provinces and the country are expanded to the cities inside them.
    geography_ids: list[int] = Field(min_length=1, max_length=100)
    source_keys: list[str] = Field(min_length=1, max_length=5)
    # Limit the run to some of the profile's segments; omit for all of them.
    segment_slugs: Optional[list[str]] = Field(default=None, min_length=1, max_length=30)
    enrich_websites: bool = True
    # Repeat searches that already finished recently instead of skipping them.
    refresh: bool = False
    # Stop spending once this many billable requests have been made.
    max_paid_requests: Optional[int] = Field(default=None, ge=1, le=100_000)

    @field_validator("geography_ids", "source_keys")
    @classmethod
    def dedupe_lists(cls, v: list) -> list:
        return _dedupe(v)

    @field_validator("segment_slugs")
    @classmethod
    def dedupe_optional_list(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return _dedupe(v) if v is not None else v


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
    # False when the run would be refused (too many searches).
    allowed: bool
    warnings: list[str]


class RunResponse(BaseModel):
    id: int
    profile_id: Optional[int] = None
    profile_name: str
    created_by_id: Optional[int] = None
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
