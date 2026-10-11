from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.core.limiter import limiter
from app.features.api_keys.dependencies import get_api_key, get_writable_api_key, rate_limit_key
from app.features.api_keys.models import ApiKey
from app.features.businesses import service as businesses_service
from app.features.businesses.dependencies import business_filters
from app.features.businesses.schemas import (
    BusinessDetailResponse,
    BusinessListResponse,
    BusinessSort,
    BusinessUpdate,
    SortDirection,
)
from app.features.businesses.service import BusinessFilters
from app.features.pipeline import service as pipeline_service
from app.features.pipeline.schemas import ActivityCreate, ActivityListResponse, ActivityResponse
from app.features.public_api import service
from app.features.public_api.schemas import PublicKeyResponse, PublicLeadCreate, PublicLeadCreated, PublicLeadUpdate
from app.features.sheets import service as sheets_service

PUBLIC_RATE_LIMIT = "120/minute"
PUBLIC_WRITE_RATE_LIMIT = "60/minute"

router = APIRouter()


@router.get("/me", response_model=PublicKeyResponse)
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=rate_limit_key)
def whoami(request: Request, key: ApiKey = Depends(get_api_key)):
    return key


@router.get("/leads", response_model=BusinessListResponse)
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=rate_limit_key)
def list_leads(
    request: Request,
    filters: BusinessFilters = Depends(business_filters),
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(businesses_service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    sort: Optional[BusinessSort] = Query(None),
    direction: Optional[SortDirection] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_api_key),
):
    return businesses_service.get_businesses(db, filters, page=page, limit=limit, sort=sort, direction=direction)


@router.get("/leads/{lead_id}", response_model=BusinessDetailResponse)
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=rate_limit_key)
def get_lead(request: Request, lead_id: int, db: Session = Depends(get_db), _=Depends(get_api_key)):
    return businesses_service.get_business_detail(db, lead_id)


@router.get("/leads/{lead_id}/activities", response_model=ActivityListResponse)
@limiter.limit(PUBLIC_RATE_LIMIT, key_func=rate_limit_key)
def list_activities(
    request: Request,
    lead_id: int,
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(pipeline_service.DEFAULT_ACTIVITY_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    _=Depends(get_api_key),
):
    return pipeline_service.get_activities(db, lead_id, page=page, limit=limit)


@router.post("/leads", response_model=PublicLeadCreated, status_code=HTTPStatus.CREATED)
@limiter.limit(PUBLIC_WRITE_RATE_LIMIT, key_func=rate_limit_key)
def create_lead(request: Request, lead_in: PublicLeadCreate, db: Session = Depends(get_db), _=Depends(get_writable_api_key)):
    created = service.create_lead(db, lead_in)
    sheets_service.notify_changed()
    return created


@router.patch("/leads/{lead_id}", response_model=BusinessDetailResponse)
@limiter.limit(PUBLIC_WRITE_RATE_LIMIT, key_func=rate_limit_key)
def update_lead(
    request: Request, lead_id: int, update_in: PublicLeadUpdate, db: Session = Depends(get_db), _=Depends(get_writable_api_key)
):
    detail = businesses_service.update_business(db, lead_id, BusinessUpdate(**update_in.model_dump(exclude_unset=True)))
    sheets_service.notify_changed()
    return detail


@router.post("/leads/{lead_id}/activities", response_model=ActivityResponse, status_code=HTTPStatus.CREATED)
@limiter.limit(PUBLIC_WRITE_RATE_LIMIT, key_func=rate_limit_key)
def add_activity(
    request: Request, lead_id: int, activity_in: ActivityCreate, db: Session = Depends(get_db), _=Depends(get_writable_api_key)
):
    return pipeline_service.add_activity(db, lead_id, activity_in, None)
