from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import NAME_MAX_LENGTH, NAME_MIN_LENGTH
from app.features.outreach.models import MessageChannel, MessageStatus, TemplateChannel
from app.features.pipeline.schemas import PersonRef

SUBJECT_MAX_LENGTH = 200
BODY_MAX_LENGTH = 2000
BLANK_BODY_MESSAGE = "Write the message text"
BLANK_NAME_MESSAGE = "Give the template a name"


class PlaceholderInfo(BaseModel):
    key: str
    label: str
    fallback: Optional[str] = None


class OutreachConfigResponse(BaseModel):
    placeholders: list[PlaceholderInfo]
    template_channels: list[TemplateChannel]
    subject_max_length: int
    body_max_length: int
    recent_days: int


class TemplateBase(BaseModel):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    channel: TemplateChannel
    subject: Optional[str] = Field(default=None, max_length=SUBJECT_MAX_LENGTH)
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < NAME_MIN_LENGTH:
            raise ValueError(BLANK_NAME_MESSAGE)
        return value

    @field_validator("body")
    @classmethod
    def body_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(BLANK_BODY_MESSAGE)
        return value.strip()

    @field_validator("subject")
    @classmethod
    def subject_trimmed(cls, value: Optional[str]) -> Optional[str]:
        return (value or "").strip() or None


class TemplateCreate(TemplateBase):
    model_config = {"extra": "forbid"}


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    channel: Optional[TemplateChannel] = None
    subject: Optional[str] = Field(default=None, max_length=SUBJECT_MAX_LENGTH)
    body: Optional[str] = Field(default=None, min_length=1, max_length=BODY_MAX_LENGTH)
    model_config = {"extra": "forbid"}


class TemplateResponse(BaseModel):
    id: int
    name: str
    channel: TemplateChannel
    subject: Optional[str] = None
    body: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class TemplateListResponse(BaseModel):
    data: list[TemplateResponse]
    count: int


class PreviewRequest(BaseModel):
    business_id: int
    template_id: Optional[int] = None
    subject: Optional[str] = Field(default=None, max_length=SUBJECT_MAX_LENGTH)
    body: Optional[str] = Field(default=None, max_length=BODY_MAX_LENGTH)
    model_config = {"extra": "forbid"}


class PreviewResponse(BaseModel):
    subject: Optional[str] = None
    body: str


class PrepareRequest(BaseModel):
    business_id: int
    contact_id: int
    channel: MessageChannel
    template_id: Optional[int] = None
    subject: Optional[str] = Field(default=None, max_length=SUBJECT_MAX_LENGTH)
    body: str = Field(min_length=1, max_length=BODY_MAX_LENGTH)
    model_config = {"extra": "forbid"}

    @field_validator("body")
    @classmethod
    def body_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(BLANK_BODY_MESSAGE)
        return value.strip()


class PrepareResponse(BaseModel):
    id: int
    channel: MessageChannel
    to_value: str
    subject: Optional[str] = None
    body: str
    link: str
    last_sent_at: Optional[datetime] = None
    last_sent_by: Optional[PersonRef] = None


class DecisionRequest(BaseModel):
    sent: bool
    model_config = {"extra": "forbid"}


class MessageResponse(BaseModel):
    id: int
    business_id: int
    business_name: str
    template_name: Optional[str] = None
    channel: MessageChannel
    to_value: str
    subject: Optional[str] = None
    body: str
    status: MessageStatus
    created_by: Optional[PersonRef] = None
    created_at: datetime
    decided_at: Optional[datetime] = None


class MessageListResponse(BaseModel):
    data: list[MessageResponse]
    count: int
