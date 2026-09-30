from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.geographies import service
from app.features.geographies.models import GeographyLevel
from app.features.geographies.schemas import (
    GeographyCreate, GeographyUpdate, GeographyResponse, GeographyListResponse, GeographyTreeNode,
)

router = APIRouter()


@router.get("/", response_model=GeographyListResponse)
def list_geographies(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    level: Optional[GeographyLevel] = Query(None),
    parent_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_geographies(db, page=page, limit=limit, search=search, level=level, parent_id=parent_id)


@router.get("/tree", response_model=list[GeographyTreeNode])
def get_geography_tree(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_geography_tree(db)


@router.post("/", response_model=GeographyResponse, status_code=201)
def create_geography(geography_in: GeographyCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.create_geography(db, geography_in)


@router.get("/{geography_id}", response_model=GeographyResponse)
def get_geography(geography_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_geography_by_id(db, geography_id)


@router.put("/{geography_id}", response_model=GeographyResponse)
def update_geography(
    geography_id: int,
    geography_in: GeographyUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.update_geography(db, geography_id, geography_in)


@router.delete("/{geography_id}", status_code=204)
def delete_geography(geography_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_geography(db, geography_id)
