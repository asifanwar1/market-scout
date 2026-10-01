import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

MASK_VISIBLE_CHARACTERS = 4



def _fernet() -> Fernet:
    if settings.ENCRYPTION_KEY:
        return Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def mask_secret(value: str) -> str:
    return f"…{value[-MASK_VISIBLE_CHARACTERS:]}" if len(value) > MASK_VISIBLE_CHARACTERS else "…"
