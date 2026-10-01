from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SPREADSHEET_MAX_LENGTH = 500
CREDENTIALS_MAX_LENGTH = 20000



class SheetsSettingsResponse(BaseModel):
    has_credentials: bool
    credentials_source: Optional[Literal["saved", "environment"]] = None
    credentials_needs_reentry: bool = False
    service_account_email: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    spreadsheet_title: Optional[str] = None
    worksheet_title: str
    auto_sync: bool
    is_configured: bool
    is_syncing: bool
    last_synced_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    last_sync_ok: Optional[bool] = None
    last_error: Optional[str] = None
    last_row_count: Optional[int] = None


class SheetsUpdate(BaseModel):
    spreadsheet: Optional[str] = Field(default=None, max_length=SPREADSHEET_MAX_LENGTH)
    auto_sync: Optional[bool] = None
    credentials_json: Optional[str] = Field(default=None, max_length=CREDENTIALS_MAX_LENGTH)
    clear_credentials: bool = False


class SheetsTestResponse(BaseModel):
    ok: bool
    message: str
