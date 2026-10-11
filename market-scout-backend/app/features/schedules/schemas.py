from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import NAME_MAX_LENGTH, NAME_MIN_LENGTH
from app.features.runs.models import RunStatus
from app.features.runs.schemas import CITIES_MAX, PAID_REQUESTS_MAX, SEGMENTS_MAX, SOURCES_MAX, dedupe_values
from app.features.schedules.models import ScheduleFrequency


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    frequency: ScheduleFrequency
    profile_id: int
    geography_ids: list[int] = Field(min_length=1, max_length=CITIES_MAX)
    source_keys: list[str] = Field(min_length=1, max_length=SOURCES_MAX)
    segment_slugs: Optional[list[str]] = Field(default=None, min_length=1, max_length=SEGMENTS_MAX)
    enrich_websites: bool = True
    max_paid_requests: Optional[int] = Field(default=None, ge=1, le=PAID_REQUESTS_MAX)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("geography_ids", "source_keys")
    @classmethod
    def dedupe_lists(cls, v: list) -> list:
        return dedupe_values(v)

    @field_validator("segment_slugs")
    @classmethod
    def dedupe_optional_list(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return dedupe_values(v) if v is not None else v


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    frequency: Optional[ScheduleFrequency] = None
    is_active: Optional[bool] = None
    profile_id: Optional[int] = None
    geography_ids: Optional[list[int]] = Field(default=None, min_length=1, max_length=CITIES_MAX)
    source_keys: Optional[list[str]] = Field(default=None, min_length=1, max_length=SOURCES_MAX)
    segment_slugs: Optional[list[str]] = Field(default=None, min_length=1, max_length=SEGMENTS_MAX)
    enrich_websites: Optional[bool] = None
    max_paid_requests: Optional[int] = Field(default=None, ge=1, le=PAID_REQUESTS_MAX)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else v

    @field_validator("geography_ids", "source_keys", "segment_slugs")
    @classmethod
    def dedupe_lists(cls, v: Optional[list]) -> Optional[list]:
        return dedupe_values(v) if v is not None else v


class LastRun(BaseModel):
    id: int
    status: RunStatus
    new_leads: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ScheduleResponse(BaseModel):
    id: int
    name: str
    profile_id: Optional[int] = None
    profile_name: str
    is_active: bool
    frequency: ScheduleFrequency
    geography_ids: list[int]
    cities: list[str]
    source_keys: list[str]
    segment_slugs: Optional[list[str]] = None
    enrich_websites: bool
    max_paid_requests: Optional[int] = None
    next_run_at: datetime
    last_run_at: Optional[datetime] = None
    last_run: Optional[LastRun] = None
    consecutive_failures: int
    last_error: Optional[str] = None
    created_at: datetime


class ScheduleListResponse(BaseModel):
    data: list[ScheduleResponse]
    count: int
