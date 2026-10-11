from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.alerts import service
from app.features.alerts.models import AlertKind
from app.features.alerts.schemas import (
    AlertListResponse,
    AlertSettings,
    AlertSettingsUpdate,
    AlertSummaryResponse,
    MarkReadRequest,
)
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=AlertListResponse)
def list_alerts(
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    unread_only: bool = Query(False),
    kind: Optional[AlertKind] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_alerts(db, current_user.id, page=page, limit=limit, unread_only=unread_only, kind=kind)


@router.get("/summary", response_model=AlertSummaryResponse)
def get_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"unread": service.count_unread(db, current_user.id)}


@router.post("/mark-read", response_model=AlertSummaryResponse)
def mark_read(body: MarkReadRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service.mark_read(db, current_user.id, body)
    return {"unread": service.count_unread(db, current_user.id)}


@router.get("/settings", response_model=AlertSettings)
def get_settings(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_settings(db)


@router.put("/settings", response_model=AlertSettings)
def update_settings(update_in: AlertSettingsUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_settings(db, update_in)
