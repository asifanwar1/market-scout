from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.features.quality.models import DuplicateConfidence, DuplicateStatus, QualityTaskKind, QualityTaskStatus

CHECK_LEADS_MAX = 500
CHECKS_PER_RUN_MAX = 2000


class QualitySettings(BaseModel):
    check_after_runs: bool = False
    max_checks_per_run: int = Field(default=200, ge=1, le=CHECKS_PER_RUN_MAX)


class QualitySettingsUpdate(BaseModel):
    check_after_runs: Optional[bool] = None
    max_checks_per_run: Optional[int] = Field(default=None, ge=1, le=CHECKS_PER_RUN_MAX)


class CheckRequest(BaseModel):
    business_ids: list[int] = Field(min_length=1, max_length=CHECK_LEADS_MAX)
    refresh: bool = False


class QualityTaskResponse(BaseModel):
    id: int
    kind: QualityTaskKind
    status: QualityTaskStatus
    total: int
    done: int
    counts: dict[str, Any]
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DuplicateSide(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    website: Optional[str] = None
    phones: list[str]
    emails: list[str]
    score: Optional[int] = None
    lead_status: str
    sources: list[str]
    rating: Optional[float] = None
    review_count: Optional[int] = None
    assigned_to: Optional[str] = None


class DuplicateResponse(BaseModel):
    id: int
    reason: str
    similarity: int
    confidence: DuplicateConfidence
    status: DuplicateStatus
    created_at: datetime
    a: DuplicateSide
    b: DuplicateSide


class DuplicateListResponse(BaseModel):
    data: list[DuplicateResponse]
    count: int


class MergeRequest(BaseModel):
    keep_id: int


class MergeResponse(BaseModel):
    kept_id: int
    removed_id: int


class ScoringTrait(BaseModel):
    key: str
    label: str
    with_count: int
    with_wins: int
    without_count: int
    without_wins: int
    win_rate_with: Optional[float] = None
    win_rate_without: Optional[float] = None
    difference: Optional[float] = None
    significant: bool
    current_weight: int
    suggested_weight: int
    note: str


class ScoringResponse(BaseModel):
    profile_id: int
    profile_name: str
    closed: int
    won: int
    lost: int
    needed: int
    enough_data: bool
    traits: list[ScoringTrait]
    can_apply: bool
    can_revert: bool


class ScoringApplyRequest(BaseModel):
    profile_id: int


class ScoringApplyResponse(BaseModel):
    weights: dict[str, int]
    rescored: int
