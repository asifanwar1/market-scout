from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.users import service
from app.features.users.models import User, UserRole
from app.features.users.schemas import UserCreate, UserListResponse, UserResponse, UserUpdate

router = APIRouter()


@router.get("/", response_model=UserListResponse)
def list_users(
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_users(db, page=page, limit=limit, search=search, role=role)


@router.post("/", response_model=UserResponse, status_code=HTTPStatus.CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.create_user(db, user_in)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_user_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    return service.update_user(db, user_id, user_in, acting_user_id=current_admin.id)
