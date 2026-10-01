from jose import JWTError
from sqlalchemy.orm import Session

from app.core.constants import TOKEN_TYPE_BEARER, TOKEN_TYPE_CLAIM, TOKEN_TYPE_REFRESH
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.features.users import service as users_service
from app.features.users.models import User


def _issue_tokens(user: User) -> dict:
    claims = {"sub": str(user.id), "tv": user.token_version}
    return {
        "access_token": create_access_token(claims),
        "refresh_token": create_refresh_token(claims),
        "token_type": TOKEN_TYPE_BEARER,
    }


def login(db: Session, email: str, password: str) -> dict:
    user = users_service.get_user_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")
    return _issue_tokens(user)


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise UnauthorizedException("Invalid refresh token") from None

    if payload.get(TOKEN_TYPE_CLAIM) != TOKEN_TYPE_REFRESH:
        raise UnauthorizedException("Invalid refresh token")

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise UnauthorizedException("Invalid refresh token") from None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active or payload.get("tv") != user.token_version:
        raise UnauthorizedException("Invalid refresh token")
    return _issue_tokens(user)


def logout_all(db: Session, user: User) -> dict:
    user.token_version += 1
    db.commit()
    return {"message": "Signed out on all devices"}


def change_password(db: Session, user: User, current_password: str, new_password: str) -> dict:
    if not verify_password(current_password, user.hashed_password):
        raise BadRequestException("Current password is incorrect")
    if verify_password(new_password, user.hashed_password):
        raise BadRequestException("New password must be different from the current password")

    user.hashed_password = hash_password(new_password)
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return _issue_tokens(user)
