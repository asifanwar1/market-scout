from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SheetsSettingsResponse(BaseModel):
    has_credentials: bool
    credentials_source: Optional[Literal["saved", "environment"]] = None
    # A saved key that can no longer be decrypted (the server secret changed).
    credentials_needs_reentry: bool = False
    # Not a secret: it is the address the person shares their Google Sheet with.
    service_account_email: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    spreadsheet_title: Optional[str] = None
    worksheet_title: str
    auto_sync: bool
    # Key and spreadsheet both present: a sync can be attempted.
    is_configured: bool
    is_syncing: bool
    last_synced_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    last_sync_ok: Optional[bool] = None
    last_error: Optional[str] = None
    last_row_count: Optional[int] = None


class SheetsUpdate(BaseModel):
    # The sheet's link or bare ID; an empty string disconnects it.
    spreadsheet: Optional[str] = Field(default=None, max_length=500)
    auto_sync: Optional[bool] = None
    # The whole downloaded service-account JSON. Stored encrypted, never returned.
    credentials_json: Optional[str] = Field(default=None, max_length=20000)
    clear_credentials: bool = False


class SheetsTestResponse(BaseModel):
    ok: bool
    message: str
