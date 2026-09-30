import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from app.config import settings


def _fernet() -> Fernet:
    if settings.ENCRYPTION_KEY:
        return Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))
    # Fernet needs a 32-byte urlsafe-base64 key; derive a stable one from SECRET_KEY.
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str | None:
    """The original value, or None if it can't be decrypted (e.g. the key was rotated)."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def mask_secret(value: str) -> str:
    return f"…{value[-4:]}" if len(value) > 4 else "…"
