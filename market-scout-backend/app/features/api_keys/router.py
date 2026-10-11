from http import HTTPStatus

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.features.api_keys import service
from app.features.api_keys.schemas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyListResponse, ApiKeyResponse
from app.features.auth.dependencies import get_current_admin_user
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=ApiKeyListResponse)
def list_keys(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.list_keys(db)


@router.post("/", response_model=ApiKeyCreatedResponse, status_code=HTTPStatus.CREATED)
def create_key(key_in: ApiKeyCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin_user)):
    key, token = service.create_key(db, key_in, admin.id)
    return {**ApiKeyResponse.model_validate(key, from_attributes=True).model_dump(), "token": token}


@router.delete("/{key_id}", response_model=ApiKeyResponse)
def revoke_key(key_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.revoke_key(db, key_id)
