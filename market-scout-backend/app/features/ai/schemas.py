from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.features.ai.models import AnalysisStatus, BatchStatus

API_KEY_MIN_LENGTH = 8
API_KEY_MAX_LENGTH = 512
BUDGET_MAX = 100_000
BATCH_SIZE_MAX = 100


class AiModelInfo(BaseModel):
    id: str
    label: str
    input_per_mtok_usd: float
    output_per_mtok_usd: float


class AiSettingsResponse(BaseModel):
    is_enabled: bool
    has_key: bool
    key_hint: Optional[str] = None
    key_source: Optional[Literal["saved", "environment"]] = None
    key_needs_reentry: bool = False
    model: str
    models: list[AiModelInfo]
    monthly_budget_usd: float
    spent_this_month_usd: float
    remaining_usd: float
    analyses_this_month: int


class AiSettingsUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    api_key: Optional[str] = Field(default=None, min_length=API_KEY_MIN_LENGTH, max_length=API_KEY_MAX_LENGTH)
    clear_api_key: bool = False
    model: Optional[str] = None
    monthly_budget_usd: Optional[float] = Field(default=None, ge=0, le=BUDGET_MAX)
    model_config = {"extra": "forbid"}

    @field_validator("api_key")
    @classmethod
    def strip_key(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else value


class AiTestResponse(BaseModel):
    ok: bool
    message: str


class AiStatusResponse(BaseModel):
    is_ready: bool
    reason: Optional[str] = None
    model_label: Optional[str] = None
    remaining_usd: float


class EstimateRequest(BaseModel):
    business_ids: list[int] = Field(min_length=1, max_length=BATCH_SIZE_MAX)
    profile_id: int
    refresh: bool = False
    model_config = {"extra": "forbid"}


class EstimateResponse(BaseModel):
    leads: int
    to_analyze: int
    without_website: int
    already_analyzed: int
    estimated_cost_usd: float
    remaining_usd: float
    within_budget: bool
    model_label: str
    warnings: list[str]


class AnalyzeRequest(EstimateRequest):
    pass


class BatchResponse(BaseModel):
    id: int
    status: BatchStatus
    total: int
    done: int
    analyzed: int
    skipped: int
    declined: int
    failed: int
    spent_usd: float
    error: Optional[str] = None
    error_samples: list[str]
    created_at: datetime
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AiResultResponse(BaseModel):
    profile_id: int
    status: AnalysisStatus
    summary: Optional[str] = None
    segment_slug: Optional[str] = None
    segment_name: Optional[str] = None
    segment_reason: Optional[str] = None
    current_segment_slug: Optional[str] = None
    fit_score: Optional[int] = None
    fit_reason: Optional[str] = None
    confidence: Optional[str] = None
    model: Optional[str] = None
    pages_read: int
    truncated: bool
    error: Optional[str] = None
    analyzed_at: datetime


class ApplySegmentRequest(BaseModel):
    profile_id: int
    model_config = {"extra": "forbid"}
