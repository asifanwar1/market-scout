from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.dependencies import get_db
from app.features.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedException() from None
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedException() from None

    # A refresh token must never be accepted as an access token.
    if payload.get("type") != "access":
        raise UnauthorizedException()

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise UnauthorizedException() from None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active or payload.get("tv") != user.token_version:
        raise UnauthorizedException() from None
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise ForbiddenException("Admin access required")
    return current_user
