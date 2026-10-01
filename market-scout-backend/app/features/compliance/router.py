from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.compliance import service
from app.features.compliance.schemas import DoNotContactCreate, DoNotContactListResponse, DoNotContactResponse
from app.features.sheets import service as sheets_service
from app.features.users.models import User

router = APIRouter()


@router.get("/do-not-contact", response_model=DoNotContactListResponse)
def list_do_not_contact(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_entries(db, page=page, limit=limit, search=search)


@router.post("/do-not-contact", response_model=DoNotContactResponse, status_code=201)
def add_do_not_contact(
    data: DoNotContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    entry = service.block_identifier(db, data, added_by_id=current_user.id)
    sheets_service.notify_changed()
    return service.to_response(db, entry)


# Anyone can record "please stop calling me"; only an admin can lift a block.
@router.delete("/do-not-contact/{entry_id}", status_code=204)
def remove_do_not_contact(entry_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.remove_entry(db, entry_id)
    sheets_service.notify_changed()
