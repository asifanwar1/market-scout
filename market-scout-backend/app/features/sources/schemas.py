from typing import Optional, Literal

from pydantic import BaseModel, Field


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
    # A saved key that can no longer be decrypted (the server secret changed).
    key_needs_reentry: bool = False
    # Enabled and, if it needs a key, has one: what a run can actually use.
    is_available: bool


class SourceListResponse(BaseModel):
    data: list[SourceResponse]
    count: int


class SourceUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    api_key: Optional[str] = Field(default=None, min_length=8, max_length=512)
    clear_api_key: bool = False


class SourceTestResponse(BaseModel):
    ok: bool
    message: str
