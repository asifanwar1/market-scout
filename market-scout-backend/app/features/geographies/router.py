from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX_LARGE, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.geographies import service
from app.features.geographies.models import GeographyLevel
from app.features.geographies.schemas import (
    GeographyCreate,
    GeographyListResponse,
    GeographyResponse,
    GeographyTreeNode,
    GeographyUpdate,
)

router = APIRouter()


@router.get("/", response_model=GeographyListResponse)
def list_geographies(
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX_LARGE),
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


@router.post("/", response_model=GeographyResponse, status_code=HTTPStatus.CREATED)
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


@router.delete("/{geography_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_geography(geography_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_geography(db, geography_id)
