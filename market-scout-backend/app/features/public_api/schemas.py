from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import NAME_MAX_LENGTH
from app.features.businesses.models import LeadStatus
from app.features.businesses.schemas import CONTACT_NAME_MAX_LENGTH, NOTES_MAX_LENGTH
from app.features.pipeline.schemas import OutcomeInput

CONTACT_LIST_MAX = 10
TEXT_MAX_LENGTH = 500
WEBSITE_MAX_LENGTH = 300
BLANK_NAME_MESSAGE = "Give the business a name"


class PublicKeyResponse(BaseModel):
    name: str
    can_write: bool


class PublicLeadUpdate(BaseModel):
    lead_status: Optional[LeadStatus] = None
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX_LENGTH)
    contact_name: Optional[str] = Field(default=None, max_length=CONTACT_NAME_MAX_LENGTH)
    outcome: Optional[OutcomeInput] = None
    model_config = {"extra": "forbid"}


class PublicLeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=NAME_MAX_LENGTH)
    phones: list[str] = Field(default_factory=list, max_length=CONTACT_LIST_MAX)
    emails: list[str] = Field(default_factory=list, max_length=CONTACT_LIST_MAX)
    website: Optional[str] = Field(default=None, max_length=WEBSITE_MAX_LENGTH)
    address: Optional[str] = Field(default=None, max_length=TEXT_MAX_LENGTH)
    city_id: Optional[int] = None
    profile_id: Optional[int] = None
    segment_slug: Optional[str] = Field(default=None, max_length=NAME_MAX_LENGTH)
    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError(BLANK_NAME_MESSAGE)
        return value


class PublicLeadCreated(BaseModel):
    id: int
    created: bool
