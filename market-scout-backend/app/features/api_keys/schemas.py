from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import NAME_MAX_LENGTH, NAME_MIN_LENGTH

BLANK_NAME_MESSAGE = "Give the key a name"


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    can_write: bool = False
    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < NAME_MIN_LENGTH:
            raise ValueError(BLANK_NAME_MESSAGE)
        return value


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    can_write: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ApiKeyCreatedResponse(ApiKeyResponse):
    token: str


class ApiKeyListResponse(BaseModel):
    data: list[ApiKeyResponse]
    count: int
