from sqlalchemy.orm import Session

from app.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.scouting.sources import google_places
from app.core.scouting.sources.base import Source
from app.core.scouting.sources.registry import (
    CATALOG,
    ENRICHMENT_KEY,
    KIND_DISCOVERY,
    SourceInfo,
    build_source,
    get_source_info,
)
from app.features.sources.models import DataSource
from app.features.sources.schemas import SourceUpdate

# Sources whose key may also come from the environment (used when none is saved in the UI).
_ENV_KEYS = {google_places.SOURCE_KEY: lambda: settings.GOOGLE_PLACES_API_KEY}


_PLACEHOLDER_DOMAINS = ("example.com", "example.org", "example.net", "test", "invalid", "localhost")


def user_agent() -> str:
    # The free public services we call ask clients to say who they are. A placeholder address is
    # worse than none: Overpass answers it with "406 Not Acceptable".
    email = settings.SCOUT_CONTACT_EMAIL.strip()
    domain = email.rpartition("@")[2].lower()
    is_placeholder = any(domain == d or domain.endswith(f".{d}") for d in _PLACEHOLDER_DOMAINS)
    contact = f" (+mailto:{email})" if email and not is_placeholder else ""
    return f"MarketScout/0.1{contact}"


def _require_info(key: str) -> SourceInfo:
    info = get_source_info(key)
    if info is None:
        raise NotFoundException("Unknown source")
    return info


def _ensure_rows(db: Session) -> dict[str, DataSource]:
    rows = {row.key: row for row in db.query(DataSource).all()}
    created = False
    for info in CATALOG:
        if info.key not in rows:
            rows[info.key] = DataSource(key=info.key, is_enabled=info.default_enabled)
            db.add(rows[info.key])
            created = True
    if created:
        db.commit()
    return rows


def ensure_sources(db: Session) -> None:
    """Create the on/off row for every catalogue source. Done once at start-up so that reading the
    Sources screen never has to write."""
    _ensure_rows(db)


def _saved_key(row: DataSource) -> tuple[str | None, bool]:
    """(plaintext key, needs_reentry)."""
    if not row.encrypted_api_key:
        return None, False
    plaintext = decrypt_secret(row.encrypted_api_key)
    return plaintext, plaintext is None


def _env_key(key: str) -> str | None:
    getter = _ENV_KEYS.get(key)
    return (getter() or None) if getter else None


def _resolve_key(row: DataSource) -> tuple[str | None, str | None, bool]:
    """(key, where it came from, saved-key-unreadable)."""
    saved, needs_reentry = _saved_key(row)
    if saved:
        return saved, "saved", False
    env = _env_key(row.key)
    if env:
        return env, "environment", needs_reentry
    return None, None, needs_reentry


def _to_view(info: SourceInfo, row: DataSource) -> dict:
    key, key_source, needs_reentry = _resolve_key(row)
    has_key = key is not None
    return {
        "key": info.key,
        "name": info.name,
        "description": info.description,
        "kind": info.kind,
        "requires_api_key": info.requires_api_key,
        "is_paid": info.is_paid,
        "is_enabled": row.is_enabled,
        "has_key": has_key,
        "key_hint": mask_secret(key) if key else None,
        "key_source": key_source,
        "key_needs_reentry": needs_reentry,
        "is_available": row.is_enabled and (has_key or not info.requires_api_key),
    }


def get_sources(db: Session) -> dict:
    rows = _ensure_rows(db)
    data = [_to_view(info, rows[info.key]) for info in CATALOG]
    return {"data": data, "count": len(data)}


def get_source(db: Session, key: str) -> dict:
    info = _require_info(key)
    return _to_view(info, _ensure_rows(db)[key])


def update_source(db: Session, key: str, update_in: SourceUpdate) -> dict:
    info = _require_info(key)
    row = _ensure_rows(db)[key]
    data = update_in.model_dump(exclude_unset=True)

    new_key = data.get("api_key")
    clear = bool(data.get("clear_api_key")) and not new_key
    if (new_key or clear) and not info.requires_api_key:
        raise BadRequestException("This source doesn't use an API key")

    # Work out the resulting state first so a rejected change leaves nothing half-applied.
    saved_after = None if clear else (new_key.strip() if new_key else _saved_key(row)[0])
    has_key_after = bool(saved_after or _env_key(key))
    enabled_after = data["is_enabled"] if data.get("is_enabled") is not None else row.is_enabled

    if info.requires_api_key and enabled_after and not has_key_after:
        if data.get("is_enabled") is True:
            raise BadRequestException("Add an API key before enabling this source")
        enabled_after = False  # its key was just removed; don't leave it switched on

    if new_key:
        row.encrypted_api_key = encrypt_secret(new_key.strip())
    elif clear:
        row.encrypted_api_key = None
    row.is_enabled = enabled_after
    db.commit()
    return _to_view(info, row)


def resolve_api_key(db: Session, key: str) -> str | None:
    return _resolve_key(_ensure_rows(db)[key])[0]


def is_available(db: Session, key: str) -> bool:
    return get_source(db, key)["is_available"]


def get_available_discovery_keys(db: Session) -> list[str]:
    rows = _ensure_rows(db)
    return [
        info.key
        for info in CATALOG
        if info.kind == KIND_DISCOVERY and _to_view(info, rows[info.key])["is_available"]
    ]


def build_sources(db: Session, keys: list[str]) -> dict[str, Source]:
    """Live source objects for the given (available) discovery keys."""
    sources: dict[str, Source] = {}
    for key in keys:
        sources[key] = build_source(
            key,
            api_key=resolve_api_key(db, key),
            user_agent=user_agent(),
            overpass_url=settings.OVERPASS_URL,
            overpass_min_interval_s=settings.OVERPASS_MIN_INTERVAL_SECONDS,
        )
    return sources


def test_source(db: Session, key: str) -> dict:
    info = _require_info(key)
    if info.kind != KIND_DISCOVERY:
        return {"ok": True, "message": "Nothing to connect to: this reads each business's own website."}
    if info.requires_api_key and resolve_api_key(db, key) is None:
        return {"ok": False, "message": "No API key saved for this source."}

    ok, message = build_sources(db, [key])[key].test_connection()
    return {"ok": ok, "message": message}


def is_enrichment_enabled(db: Session) -> bool:
    return is_available(db, ENRICHMENT_KEY)
