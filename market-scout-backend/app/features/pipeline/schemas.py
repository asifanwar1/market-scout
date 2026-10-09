from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.features.pipeline.models import ActivityKind, LossReason, ManualActivityKind, OutcomeKind

SUMMARY_MAX_LENGTH = 2000
TITLE_MAX_LENGTH = 200
PRODUCT_MAX_LENGTH = 120
OUTCOME_NOTE_MAX_LENGTH = 1000
VALUE_MAX = 1_000_000_000


class PersonRef(BaseModel):
    id: int
    full_name: str


class OutcomeInput(BaseModel):
    value: Optional[float] = Field(default=None, ge=0, le=VALUE_MAX)
    product: Optional[str] = Field(default=None, max_length=PRODUCT_MAX_LENGTH)
    loss_reason: Optional[LossReason] = None
    note: Optional[str] = Field(default=None, max_length=OUTCOME_NOTE_MAX_LENGTH)
    model_config = {"extra": "forbid"}


class OutcomeResponse(BaseModel):
    kind: OutcomeKind
    value: Optional[float] = None
    product: Optional[str] = None
    loss_reason: Optional[LossReason] = None
    note: Optional[str] = None
    closed_at: datetime
    closed_by: Optional[PersonRef] = None


class ActivityCreate(BaseModel):
    kind: ManualActivityKind
    summary: str = Field(min_length=1, max_length=SUMMARY_MAX_LENGTH)
    model_config = {"extra": "forbid"}

    @field_validator("summary")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Write something to log")
        return value


class ActivityResponse(BaseModel):
    id: int
    kind: ActivityKind
    summary: Optional[str] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    created_by: Optional[PersonRef] = None
    created_at: datetime


class ActivityListResponse(BaseModel):
    data: list[ActivityResponse]
    count: int


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    due_on: date
    assigned_to_id: Optional[int] = None
    model_config = {"extra": "forbid"}

    @field_validator("title")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Give the task a title")
        return value


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX_LENGTH)
    due_on: Optional[date] = None
    assigned_to_id: Optional[int] = None
    done: Optional[bool] = None
    model_config = {"extra": "forbid"}

    @field_validator("title")
    @classmethod
    def not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Give the task a title")
        return value


class TaskResponse(BaseModel):
    id: int
    business_id: int
    business_name: str
    title: str
    due_on: date
    assigned_to: Optional[PersonRef] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class TaskListResponse(BaseModel):
    data: list[TaskResponse]
    count: int


class TaskSummaryResponse(BaseModel):
    overdue: int
    due_today: int
    open: int


class PipelineConfigResponse(BaseModel):
    deal_currency: str
