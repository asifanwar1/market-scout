from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.businesses import service
from app.features.businesses.dependencies import business_filters
from app.features.businesses.schemas import (
    AssignedUser,
    BulkBusinessDelete,
    BulkBusinessUpdate,
    BulkDeleteResponse,
    BulkUpdateResponse,
    BusinessDetailResponse,
    BusinessListResponse,
    BusinessSort,
    BusinessUpdate,
    SortDirection,
)
from app.features.businesses.service import BusinessFilters
from app.features.compliance import service as compliance_service
from app.features.compliance.schemas import BusinessDoNotContactCreate, DoNotContactResponse
from app.features.sheets import service as sheets_service
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=BusinessListResponse)
def list_businesses(
    filters: BusinessFilters = Depends(business_filters),
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    sort: Optional[BusinessSort] = Query(None),
    direction: Optional[SortDirection] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_businesses(db, filters, page=page, limit=limit, sort=sort, direction=direction)


@router.get("/assignees", response_model=list[AssignedUser])
def list_assignees(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_assignable_users(db)


@router.post("/bulk-update", response_model=BulkUpdateResponse)
def bulk_update_businesses(
    update_in: BulkBusinessUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    updated = service.bulk_update_businesses(db, update_in, current_user.id)
    sheets_service.notify_changed()
    return {"updated": updated}


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_businesses(delete_in: BulkBusinessDelete, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    deleted = service.bulk_delete_businesses(db, delete_in)
    sheets_service.notify_changed()
    return {"deleted": deleted}


@router.get("/{business_id}", response_model=BusinessDetailResponse)
def get_business(business_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_business_detail(db, business_id)


@router.patch("/{business_id}", response_model=BusinessDetailResponse)
def update_business(
    business_id: int,
    update_in: BusinessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = service.update_business(db, business_id, update_in, current_user.id)
    sheets_service.notify_changed()
    return business


@router.delete("/{business_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_business(business_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_business(db, business_id)
    sheets_service.notify_changed()


@router.post("/{business_id}/do-not-contact", response_model=DoNotContactResponse, status_code=HTTPStatus.CREATED)
def mark_do_not_contact(
    business_id: int,
    data: BusinessDoNotContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = compliance_service.block_business(db, business_id, data.reason, added_by_id=current_user.id)
    sheets_service.notify_changed()
    return compliance_service.to_response(db, entry)
