from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.sources import service
from app.features.sources.schemas import SourceListResponse, SourceResponse, SourceTestResponse, SourceUpdate

router = APIRouter()


@router.get("/", response_model=SourceListResponse)
def list_sources(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_sources(db)


@router.get("/{key}", response_model=SourceResponse)
def get_source(key: str, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_source(db, key)


@router.put("/{key}", response_model=SourceResponse)
def update_source(key: str, source_in: SourceUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_source(db, key, source_in)


@router.post("/{key}/test", response_model=SourceTestResponse)
def test_source(key: str, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.test_source(db, key)
