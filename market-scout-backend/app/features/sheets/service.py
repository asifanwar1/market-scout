"""The live Google Sheet: a one-way mirror of the leads (app -> sheet).

Every sync rewrites the whole "Leads" worksheet from the database, so the sheet is always exactly
what the app would export and running it twice changes nothing. Edits made in the sheet are
overwritten; sales work in the app.
"""
import logging
import re
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.exceptions import BadRequestException, ConflictException
from app.core.sheets.client import SheetsClient
from app.core.sheets.errors import SheetsError
from app.core.sheets.service_account import ServiceAccount, parse_service_account
from app.database import SessionLocal, WriteSessionLocal
from app.features.businesses.schemas import BusinessSort
from app.features.businesses.service import BusinessFilters
from app.features.exports import service as exports_service
from app.features.sheets.models import AppSetting
from app.features.sheets.schemas import SheetsUpdate

logger = logging.getLogger(__name__)

WORKSHEET_TITLE = "Leads"
_CONFIG_KEY = "sheets"
_CREDENTIALS_KEY = "sheets_credentials"

_ID_IN_URL = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]{15,})")
_BARE_ID = re.compile(r"^[A-Za-z0-9_-]{15,}$")

# Held while a sync runs, so two never write the sheet at once. Manual "Sync now" refuses when it
# is taken; the automatic path waits its turn.
_sync_lock = threading.Lock()
_timer_lock = threading.Lock()
_pending_timer: threading.Timer | None = None


# ---- stored settings ---------------------------------------------------------------------------

def _read(db: Session, key: str) -> dict:
    row = db.get(AppSetting, key)
    return dict(row.value) if row is not None and row.value else {}


def _write(db: Session, key: str, value: dict) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value  # a new dict, so the JSON column notices the change
    db.commit()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_credentials(db: Session) -> tuple[ServiceAccount | None, str | None, bool]:
    """(the account, where it came from, saved-key-unreadable)."""
    saved = _read(db, _CREDENTIALS_KEY).get("encrypted")
    needs_reentry = False
    if saved:
        plaintext = decrypt_secret(saved)
        if plaintext is None:
            needs_reentry = True
        else:
            try:
                return parse_service_account(plaintext), "saved", False
            except SheetsError:
                needs_reentry = True
    if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            return parse_service_account(settings.GOOGLE_SERVICE_ACCOUNT_JSON), "environment", needs_reentry
        except SheetsError:
            logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON is set but isn't a usable service-account key")
    return None, None, needs_reentry


def parse_spreadsheet_id(text: str) -> str:
    text = text.strip()
    match = _ID_IN_URL.search(text)
    if match:
        return match.group(1)
    if _BARE_ID.match(text):
        return text
    raise BadRequestException(
        "That doesn't look like a Google Sheets link or ID. Open the sheet in your browser and copy the address from the top."
    )


def get_settings(db: Session) -> dict:
    config = _read(db, _CONFIG_KEY)
    account, source, needs_reentry = _resolve_credentials(db)
    spreadsheet_id = config.get("spreadsheet_id")
    return {
        "has_credentials": account is not None,
        "credentials_source": source,
        "credentials_needs_reentry": needs_reentry,
        "service_account_email": account.client_email if account else None,
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}" if spreadsheet_id else None,
        "spreadsheet_title": config.get("spreadsheet_title"),
        "worksheet_title": WORKSHEET_TITLE,
        "auto_sync": bool(config.get("auto_sync", True)),
        "is_configured": account is not None and bool(spreadsheet_id),
        "is_syncing": _sync_lock.locked(),
        "last_synced_at": config.get("last_synced_at"),
        "last_attempt_at": config.get("last_attempt_at"),
        "last_sync_ok": config.get("last_sync_ok"),
        "last_error": config.get("last_error"),
        "last_row_count": config.get("last_row_count"),
    }


def update_settings(db: Session, update_in: SheetsUpdate) -> dict:
    data = update_in.model_dump(exclude_unset=True)
    config = _read(db, _CONFIG_KEY)

    # Validate everything before storing anything, so a rejected change leaves nothing half-saved.
    new_credentials = (data.get("credentials_json") or "").strip()
    if new_credentials:
        try:
            parse_service_account(new_credentials)
        except SheetsError as exc:
            raise BadRequestException(str(exc)) from exc
    new_spreadsheet_id = None
    if data.get("spreadsheet") is not None and data["spreadsheet"].strip():
        new_spreadsheet_id = parse_spreadsheet_id(data["spreadsheet"])

    if new_credentials:
        _write(db, _CREDENTIALS_KEY, {"encrypted": encrypt_secret(new_credentials)})
    elif data.get("clear_credentials"):
        _write(db, _CREDENTIALS_KEY, {})

    if "spreadsheet" in data:
        if new_spreadsheet_id != config.get("spreadsheet_id"):
            # A different sheet: what we knew about the old one no longer applies.
            config = {"auto_sync": config.get("auto_sync", True), "spreadsheet_id": new_spreadsheet_id}
    if data.get("auto_sync") is not None:
        config["auto_sync"] = data["auto_sync"]
    if new_credentials or data.get("clear_credentials"):
        # New account, new permissions: forget the last outcome and the "unchanged" shortcut.
        for stale in ("last_sync_ok", "last_error", "content_hash", "spreadsheet_title"):
            config.pop(stale, None)
    _write(db, _CONFIG_KEY, config)
    return get_settings(db)


# ---- talking to Google --------------------------------------------------------------------------------

def _build_client(account: ServiceAccount) -> SheetsClient:
    return SheetsClient(account, api_base=settings.SHEETS_API_URL, token_url=settings.GOOGLE_TOKEN_URL)


def _require_configured(db: Session) -> tuple[ServiceAccount, dict]:
    config = _read(db, _CONFIG_KEY)
    account, _, needs_reentry = _resolve_credentials(db)
    if account is None:
        raise BadRequestException(
            "The saved Google key can't be read any more. Paste it again." if needs_reentry
            else "Add the Google service-account key first."
        )
    if not config.get("spreadsheet_id"):
        raise BadRequestException("Add the link of the Google Sheet first.")
    return account, config


def test_connection(db: Session) -> dict:
    account, config = _require_configured(db)
    try:
        with _build_client(account) as client:
            title = client.spreadsheet_title(config["spreadsheet_id"])
    except SheetsError as exc:
        return {"ok": False, "message": str(exc)}
    _write(db, _CONFIG_KEY, {**_read(db, _CONFIG_KEY), "spreadsheet_title": title})
    return {"ok": True, "message": f'Connected. Found the spreadsheet "{title}".'}


# ---- syncing ---------------------------------------------------------------------------------------------

def _sync_locked(db: Session, force: bool) -> None:
    """Rewrite the worksheet and record what happened. The sync lock must be held. Never raises:
    the outcome, good or bad, is stored for the settings screen."""
    config = _read(db, _CONFIG_KEY)
    account, _, _ = _resolve_credentials(db)
    spreadsheet_id = config.get("spreadsheet_id")
    if account is None or not spreadsheet_id:
        return

    config["last_attempt_at"] = _now_iso()
    try:
        rows = list(exports_service.iter_lead_rows(db, BusinessFilters(), sort=BusinessSort.SCORE))
        fingerprint = exports_service.rows_fingerprint(exports_service.LEAD_HEADERS, rows)
        if not force and config.get("last_sync_ok") and config.get("content_hash") == fingerprint:
            return  # nothing changed since the last successful sync

        # The rows are plain values now; end this read transaction before the slow Google calls so
        # nothing is held open (or left with a stale snapshot) while we wait on the network.
        db.rollback()
        with _build_client(account) as client:
            title = client.spreadsheet_title(spreadsheet_id)
            written = client.replace_worksheet(spreadsheet_id, WORKSHEET_TITLE, exports_service.LEAD_HEADERS, rows)
        config.update(
            spreadsheet_title=title, content_hash=fingerprint, last_row_count=written,
            last_sync_ok=True, last_error=None, last_synced_at=_now_iso(),
        )
    except SheetsError as exc:
        config.update(last_sync_ok=False, last_error=str(exc))
    except Exception:
        logger.exception("Google Sheets sync failed")
        db.rollback()
        config.update(last_sync_ok=False, last_error="Unexpected error (see the server log).")
    finally:
        # A short write transaction of its own. Merge over whatever was saved meanwhile (someone may
        # have changed the link mid-sync).
        with _session(write=True) as write_db:
            latest = _read(write_db, _CONFIG_KEY)
            if latest.get("spreadsheet_id") == spreadsheet_id:
                _write(write_db, _CONFIG_KEY, {**latest, **{k: v for k, v in config.items() if k != "auto_sync"}})


@contextmanager
def _session(write: bool = False) -> Iterator[Session]:
    db = (WriteSessionLocal if write else SessionLocal)()
    try:
        yield db
    finally:
        db.close()


def _launch(target: Callable[[], None]) -> None:
    threading.Thread(target=target, name="sheets-sync", daemon=True).start()


def _manual_sync() -> None:
    try:
        with _session() as db:
            _sync_locked(db, force=True)
    finally:
        _sync_lock.release()


def start_sync(db: Session) -> dict:
    """"Sync now": starts the sync in the background and returns straight away; the settings
    screen watches ``is_syncing`` and then shows the outcome."""
    _require_configured(db)
    if not _sync_lock.acquire(blocking=False):
        raise ConflictException("A sync is already running.")
    try:
        _launch(_manual_sync)
    except Exception:
        _sync_lock.release()
        raise
    return get_settings(db)


def sync_now(db: Session, force: bool = True) -> dict:
    """Blocking sync on the caller's session (tests; the app itself goes through the background paths)."""
    _require_configured(db)
    with _sync_lock:
        _sync_locked(db, force=force)
    return get_settings(db)


# ---- keeping it live ----------------------------------------------------------------------------------------

def _schedule(delay: float, target: Callable[[], None]) -> threading.Timer:
    timer = threading.Timer(delay, target)
    timer.daemon = True
    timer.start()
    return timer


def _auto_sync() -> None:
    try:
        with _session() as db:
            config = _read(db, _CONFIG_KEY)
            if not config.get("auto_sync", True) or not config.get("spreadsheet_id"):
                return
            with _sync_lock:
                _sync_locked(db, force=False)
    except Exception:
        logger.exception("Automatic Google Sheets sync crashed")


def _fire() -> None:
    global _pending_timer
    with _timer_lock:
        _pending_timer = None  # edits from here on schedule a fresh sync
    _auto_sync()


def notify_changed() -> None:
    """Leads changed (a run finished, a lead was edited, someone was put on do-not-contact).
    Refreshes the sheet shortly afterwards if it is connected; a burst of changes shares one
    refresh. Cheap and never raises, so callers can fire it after any change."""
    global _pending_timer
    delay = settings.SHEETS_AUTO_SYNC_DELAY_SECONDS
    if delay < 0:
        return
    try:
        with _timer_lock:
            if _pending_timer is None:
                _pending_timer = _schedule(delay, _fire)
    except Exception:
        logger.exception("Couldn't schedule the Google Sheets refresh")
