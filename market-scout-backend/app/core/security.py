from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from app.core.config import settings
from app.core.constants import TOKEN_TYPE_ACCESS, TOKEN_TYPE_CLAIM, TOKEN_TYPE_REFRESH

PASSWORD_SPECIAL_CHARACTERS = "!@#$%^&*()-_=+[]{}|;:,.<>?"



def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


def validate_password_strength(value: str) -> str:
    if not any(c.isupper() for c in value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one digit")
    if not any(c in PASSWORD_SPECIAL_CHARACTERS for c in value):
        raise ValueError("Password must contain at least one special character")
    return value


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, TOKEN_TYPE_CLAIM: TOKEN_TYPE_ACCESS})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, TOKEN_TYPE_CLAIM: TOKEN_TYPE_REFRESH})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
