import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.features.api_keys.models import ApiKey
from app.features.api_keys.schemas import ApiKeyCreate

TOKEN_PREFIX = "ms_"
TOKEN_BYTES = 32
DISPLAY_PREFIX_LENGTH = 11
LAST_USED_REFRESH_SECONDS = 60
KEY_NOT_FOUND_MESSAGE = "API key not found"


def _now() -> datetime:
    return datetime.now(UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_key(db: Session, key_in: ApiKeyCreate, actor_id: int) -> tuple[ApiKey, str]:
    token = TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_BYTES)
    key = ApiKey(
        name=key_in.name, prefix=token[:DISPLAY_PREFIX_LENGTH], key_hash=hash_token(token), can_write=key_in.can_write,
        created_by_id=actor_id,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key, token


def list_keys(db: Session) -> dict:
    rows = db.query(ApiKey).order_by(ApiKey.revoked_at.isnot(None), ApiKey.created_at.desc(), ApiKey.id.desc()).all()
    return {"data": rows, "count": len(rows)}


def revoke_key(db: Session, key_id: int) -> ApiKey:
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if key is None:
        raise NotFoundException(KEY_NOT_FOUND_MESSAGE)
    if key.revoked_at is None:
        key.revoked_at = _now()
        db.commit()
        db.refresh(key)
    return key


def find_active_key(db: Session, token: str) -> ApiKey | None:
    if not token.startswith(TOKEN_PREFIX):
        return None
    return db.query(ApiKey).filter(ApiKey.key_hash == hash_token(token), ApiKey.revoked_at.is_(None)).first()


def touch(db: Session, key: ApiKey) -> None:
    now = _now()
    last = key.last_used_at
    if last is not None:
        last = last if last.tzinfo is not None else last.replace(tzinfo=UTC)
        if now - last < timedelta(seconds=LAST_USED_REFRESH_SECONDS):
            return
    key.last_used_at = now
    db.commit()
