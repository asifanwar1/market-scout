from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.profiles import service
from app.features.profiles.schemas import ProfileCreate, ProfileListResponse, ProfileResponse, ProfileUpdate

router = APIRouter()


@router.get("/", response_model=ProfileListResponse)
def list_profiles(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_profiles(db, page=page, limit=limit, search=search, is_active=is_active)


@router.post("/", response_model=ProfileResponse, status_code=201)
def create_profile(profile_in: ProfileCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.create_profile(db, profile_in)


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_profile_by_id(db, profile_id)


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: int,
    profile_in: ProfileUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.update_profile(db, profile_id, profile_in)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_profile(db, profile_id)
