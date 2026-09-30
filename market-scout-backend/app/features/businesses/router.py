from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.businesses import service
from app.features.businesses.models import LeadStatus
from app.features.businesses.schemas import (
    AssignedUser, BulkBusinessUpdate, BulkUpdateResponse, BusinessDetailResponse, BusinessListResponse,
    BusinessSort, BusinessUpdate, SortDirection,
)
from app.features.businesses.service import BusinessFilters
from app.features.compliance import service as compliance_service
from app.features.compliance.schemas import BusinessDoNotContactCreate, DoNotContactResponse
from app.features.users.models import User

router = APIRouter()


def business_filters(
    profile_id: Optional[int] = Query(None),
    segment: Optional[str] = Query(None, description="Segment slug; needs profile_id"),
    geography_id: Optional[int] = Query(None, description="A city, or a province/country for every city inside"),
    has_phone: Optional[bool] = Query(None),
    whatsapp_likely: Optional[bool] = Query(None),
    has_email: Optional[bool] = Query(None),
    has_website: Optional[bool] = Query(None),
    status: Optional[LeadStatus] = Query(None),
    assigned_to_id: Optional[int] = Query(None),
    unassigned: bool = Query(False),
    source: Optional[str] = Query(None, description="Only businesses this source reported"),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    search: Optional[str] = Query(None, max_length=100, description="Name, address, phone or email"),
) -> BusinessFilters:
    return BusinessFilters(
        profile_id=profile_id, segment=segment, geography_id=geography_id, has_phone=has_phone,
        whatsapp_likely=whatsapp_likely, has_email=has_email, has_website=has_website, status=status,
        assigned_to_id=assigned_to_id, unassigned=unassigned, source=source, min_score=min_score, search=search,
    )


@router.get("/", response_model=BusinessListResponse)
def list_businesses(
    filters: BusinessFilters = Depends(business_filters),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort: Optional[BusinessSort] = Query(None),
    direction: Optional[SortDirection] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_businesses(db, filters, page=page, limit=limit, sort=sort, direction=direction)


# Static paths before "/{business_id}" so they aren't parsed as an id.
@router.get("/assignees", response_model=list[AssignedUser])
def list_assignees(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_assignable_users(db)


@router.post("/bulk-update", response_model=BulkUpdateResponse)
def bulk_update_businesses(update_in: BulkBusinessUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {"updated": service.bulk_update_businesses(db, update_in)}


@router.get("/{business_id}", response_model=BusinessDetailResponse)
def get_business(business_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_business_detail(db, business_id)


@router.patch("/{business_id}", response_model=BusinessDetailResponse)
def update_business(
    business_id: int, update_in: BusinessUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    return service.update_business(db, business_id, update_in)


@router.post("/{business_id}/do-not-contact", response_model=DoNotContactResponse, status_code=201)
def mark_do_not_contact(
    business_id: int,
    data: BusinessDoNotContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = compliance_service.block_business(db, business_id, data.reason, added_by_id=current_user.id)
    return compliance_service.to_response(db, entry)
