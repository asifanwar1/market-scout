from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.features.imports.models import ImportStatus

COLUMNS_PER_FIELD_MAX = 8
LABEL_MIN_LENGTH = 2
LABEL_MAX_LENGTH = 60



class ColumnMapping(BaseModel):
    name: str = Field(min_length=1)
    phones: list[str] = Field(default_factory=list, max_length=COLUMNS_PER_FIELD_MAX)
    emails: list[str] = Field(default_factory=list, max_length=COLUMNS_PER_FIELD_MAX)
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    category: Optional[str] = None

    @field_validator("website", "address", "city", "latitude", "longitude", "category")
    @classmethod
    def blank_means_unmapped(cls, value: Optional[str]) -> Optional[str]:
        return value or None


class ImportOptions(BaseModel):
    label: str = Field(min_length=LABEL_MIN_LENGTH, max_length=LABEL_MAX_LENGTH)
    profile_id: int
    segment_slug: Optional[str] = None
    default_geography_id: Optional[int] = None
    require_contact: bool = True
    lookup_contacts: bool = False
    mapping: ColumnMapping

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str) -> str:
        label = " ".join(value.split())
        if len(label) < LABEL_MIN_LENGTH:
            raise ValueError(f"Give the list a name of at least {LABEL_MIN_LENGTH} characters")
        return label


class ImportPreviewResponse(BaseModel):
    filename: str
    columns: list[str]
    row_count: int
    sample: list[dict[str, str]]
    suggested_mapping: dict


class ImportResponse(BaseModel):
    id: int
    label: str
    source_key: str
    filename: str
    profile_id: Optional[int] = None
    profile_name: str
    segment_slug: Optional[str] = None
    default_geography_id: Optional[int] = None
    default_geography_name: Optional[str] = None
    require_contact: bool
    lookup_contacts: bool = False
    status: ImportStatus
    rows_total: int
    rows_to_import: int
    rows_done: int
    progress_percent: int
    skipped: dict[str, int]
    stats: dict[str, int]
    error: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ImportListResponse(BaseModel):
    data: list[ImportResponse]
    count: int
