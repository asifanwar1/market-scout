from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.limiter import limiter, login_rate_limit_key
from app.features.auth import service
from app.features.auth.dependencies import get_current_user
from app.features.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
)
from app.features.users.models import User
from app.features.users.schemas import UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute", key_func=login_rate_limit_key)
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    return service.login(db, login_data.email, login_data.password)


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
@limiter.limit("10/minute", key_func=login_rate_limit_key)
def token_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return service.login(db, form_data.username, form_data.password)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, refresh_data: RefreshRequest, db: Session = Depends(get_db)):
    return service.refresh_tokens(db, refresh_data.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", response_model=TokenResponse)
@limiter.limit("5/minute")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.change_password(db, current_user, data.current_password, data.new_password)


@router.post("/logout-all", response_model=MessageResponse)
@limiter.limit("20/minute")
def logout_all(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.logout_all(db, current_user)
