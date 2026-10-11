from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import NAME_MAX_LENGTH, NAME_MIN_LENGTH
from app.features.webhooks.models import DeliveryStatus, WebhookEvent

URL_MAX_LENGTH = 500
BLANK_NAME_MESSAGE = "Give the webhook a name"
NO_EVENTS_MESSAGE = "Choose at least one event"
PING_NOT_SUBSCRIBABLE_MESSAGE = "ping is only sent by the test button"


def _check_events(events: list[WebhookEvent]) -> list[WebhookEvent]:
    unique = list(dict.fromkeys(events))
    if not unique:
        raise ValueError(NO_EVENTS_MESSAGE)
    if WebhookEvent.PING in unique:
        raise ValueError(PING_NOT_SUBSCRIBABLE_MESSAGE)
    return unique


class EventInfo(BaseModel):
    key: WebhookEvent
    label: str
    description: str


class WebhookConfigResponse(BaseModel):
    events: list[EventInfo]
    max_attempts: int
    disable_after_failures: int
    allow_private_urls: bool


class WebhookCreate(BaseModel):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    url: str = Field(min_length=1, max_length=URL_MAX_LENGTH)
    events: list[WebhookEvent]
    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < NAME_MIN_LENGTH:
            raise ValueError(BLANK_NAME_MESSAGE)
        return value

    @field_validator("url")
    @classmethod
    def url_trimmed(cls, value: str) -> str:
        return value.strip()

    @field_validator("events")
    @classmethod
    def events_valid(cls, value: list[WebhookEvent]) -> list[WebhookEvent]:
        return _check_events(value)


class WebhookUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    url: Optional[str] = Field(default=None, min_length=1, max_length=URL_MAX_LENGTH)
    events: Optional[list[WebhookEvent]] = None
    is_active: Optional[bool] = None
    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if len(value) < NAME_MIN_LENGTH:
            raise ValueError(BLANK_NAME_MESSAGE)
        return value

    @field_validator("url")
    @classmethod
    def url_trimmed(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value is not None else value

    @field_validator("events")
    @classmethod
    def events_valid(cls, value: Optional[list[WebhookEvent]]) -> Optional[list[WebhookEvent]]:
        return _check_events(value) if value is not None else value


class WebhookResponse(BaseModel):
    id: int
    name: str
    url: str
    events: list[WebhookEvent]
    is_active: bool
    consecutive_failures: int
    last_delivery_at: Optional[datetime] = None
    last_status_code: Optional[int] = None
    last_error: Optional[str] = None
    secret_hint: str
    created_at: datetime


class WebhookCreatedResponse(WebhookResponse):
    secret: str


class WebhookListResponse(BaseModel):
    data: list[WebhookResponse]
    count: int


class DeliveryResponse(BaseModel):
    id: int
    webhook_id: int
    event: WebhookEvent
    status: DeliveryStatus
    attempts: int
    next_attempt_at: Optional[datetime] = None
    response_status: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    delivered_at: Optional[datetime] = None


class DeliveryListResponse(BaseModel):
    data: list[DeliveryResponse]
    count: int
