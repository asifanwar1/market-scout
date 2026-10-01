from typing import Literal, Optional

from pydantic import BaseModel, Field

API_KEY_MIN_LENGTH = 8
API_KEY_MAX_LENGTH = 512



class SourceResponse(BaseModel):
    key: str
    name: str
    description: str
    kind: Literal["discovery", "enrichment"]
    requires_api_key: bool
    is_paid: bool
    is_enabled: bool
    has_key: bool
    key_hint: Optional[str] = None
    key_source: Optional[Literal["saved", "environment"]] = None
    key_needs_reentry: bool = False
    requires_dataset: bool = False
    dataset_ready: bool = True
    dataset_note: Optional[str] = None
    is_available: bool


class SourceListResponse(BaseModel):
    data: list[SourceResponse]
    count: int


class SourceUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    api_key: Optional[str] = Field(default=None, min_length=API_KEY_MIN_LENGTH, max_length=API_KEY_MAX_LENGTH)
    clear_api_key: bool = False


class SourceTestResponse(BaseModel):
    ok: bool
    message: str
