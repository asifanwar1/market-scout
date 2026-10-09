from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.features.businesses.models import ContactKind, LeadStatus
from app.features.pipeline.schemas import OutcomeInput, OutcomeResponse

NOTES_MAX_LENGTH = 5000
BULK_UPDATE_MAX = 500



class BusinessSort(str, Enum):
    SCORE = "score"
    NEWEST = "newest"
    LAST_SEEN = "last_seen"
    NAME = "name"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class AssignedUser(BaseModel):
    id: int
    full_name: str


class ClassificationResponse(BaseModel):
    profile_id: int
    segment_slug: Optional[str] = None
    segment_name: Optional[str] = None
    score: int


class ContactPointResponse(BaseModel):
    id: int
    kind: ContactKind
    value: str
    is_mobile: bool
    whatsapp_likely: bool
    source_key: str
    created_at: Optional[datetime] = None


class SourceRecordResponse(BaseModel):
    source_key: str
    external_id: str
    run_id: Optional[int] = None
    fetched_at: datetime


class BusinessListItem(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    profile_id: Optional[int] = None
    segment_slug: Optional[str] = None
    segment_name: Optional[str] = None
    score: Optional[int] = None
    lead_status: LeadStatus
    assigned_to: Optional[AssignedUser] = None
    primary_phone: Optional[str] = None
    whatsapp_likely: bool
    email: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    sources: list[str]
    first_seen_at: datetime
    last_seen_at: datetime


class BusinessListResponse(BaseModel):
    data: list[BusinessListItem]
    count: int


class BusinessDetailResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    city_id: Optional[int] = None
    city: Optional[str] = None
    province: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    categories: list[str]
    lead_status: LeadStatus
    assigned_to: Optional[AssignedUser] = None
    notes: Optional[str] = None
    outcome: Optional[OutcomeResponse] = None
    classifications: list[ClassificationResponse]
    contacts: list[ContactPointResponse]
    sources: list[SourceRecordResponse]
    first_seen_at: datetime
    last_seen_at: datetime
    enriched_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BusinessUpdate(BaseModel):
    lead_status: Optional[LeadStatus] = None
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX_LENGTH)
    assigned_to_id: Optional[int] = None
    outcome: Optional[OutcomeInput] = None


class BulkBusinessUpdate(BaseModel):
    business_ids: list[int] = Field(min_length=1, max_length=BULK_UPDATE_MAX)
    lead_status: Optional[LeadStatus] = None
    assigned_to_id: Optional[int] = None
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def something_to_change(self) -> "BulkBusinessUpdate":
        if not ({"lead_status", "assigned_to_id"} & self.model_fields_set):
            raise ValueError("Send lead_status and/or assigned_to_id")
        return self


class BulkUpdateResponse(BaseModel):
    updated: int


class BulkBusinessDelete(BaseModel):
    business_ids: list[int] = Field(min_length=1, max_length=BULK_UPDATE_MAX)
    model_config = {"extra": "forbid"}


class BulkDeleteResponse(BaseModel):
    deleted: int
