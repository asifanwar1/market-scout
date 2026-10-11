from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.constants import SCORE_MAX, SCORE_MIN
from app.features.alerts.models import AlertKind

NEW_REVIEWS_MAX = 10_000
PERCENT_GROWTH_MAX = 1_000
ALERTS_PER_RUN_MAX = 500


class AlertSettings(BaseModel):
    new_lead_enabled: bool = True
    new_lead_min_score: int = Field(default=70, ge=SCORE_MIN, le=SCORE_MAX)
    growing_enabled: bool = True
    growing_min_new_reviews: int = Field(default=10, ge=1, le=NEW_REVIEWS_MAX)
    growing_min_percent: int = Field(default=20, ge=0, le=PERCENT_GROWTH_MAX)
    reachable_enabled: bool = True
    max_per_run: int = Field(default=50, ge=1, le=ALERTS_PER_RUN_MAX)


class AlertSettingsUpdate(BaseModel):
    new_lead_enabled: Optional[bool] = None
    new_lead_min_score: Optional[int] = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)
    growing_enabled: Optional[bool] = None
    growing_min_new_reviews: Optional[int] = Field(default=None, ge=1, le=NEW_REVIEWS_MAX)
    growing_min_percent: Optional[int] = Field(default=None, ge=0, le=PERCENT_GROWTH_MAX)
    reachable_enabled: Optional[bool] = None
    max_per_run: Optional[int] = Field(default=None, ge=1, le=ALERTS_PER_RUN_MAX)


class AlertResponse(BaseModel):
    id: int
    kind: AlertKind
    message: str
    detail: dict[str, Any]
    business_id: int
    business_name: str
    city: Optional[str] = None
    run_id: Optional[int] = None
    is_read: bool
    created_at: datetime


class AlertListResponse(BaseModel):
    data: list[AlertResponse]
    count: int
    unread: int


class AlertSummaryResponse(BaseModel):
    unread: int


class MarkReadRequest(BaseModel):
    ids: Optional[list[int]] = Field(default=None, max_length=500)
    all: bool = False
