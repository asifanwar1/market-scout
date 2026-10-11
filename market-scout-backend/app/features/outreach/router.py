from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.outreach import service
from app.features.outreach.models import MessageStatus, TemplateChannel
from app.features.outreach.schemas import (
    DecisionRequest,
    MessageListResponse,
    MessageResponse,
    OutreachConfigResponse,
    PrepareRequest,
    PrepareResponse,
    PreviewRequest,
    PreviewResponse,
    TemplateCreate,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdate,
)
from app.features.users.models import User

router = APIRouter()


@router.get("/config", response_model=OutreachConfigResponse)
def get_config(_=Depends(get_current_user)):
    return service.get_config()


@router.get("/templates", response_model=TemplateListResponse)
def list_templates(
    channel: Optional[TemplateChannel] = Query(None), db: Session = Depends(get_db), _=Depends(get_current_user)
):
    return service.list_templates(db, channel)


@router.post("/templates", response_model=TemplateResponse, status_code=HTTPStatus.CREATED)
def create_template(
    template_in: TemplateCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin_user)
):
    return service.create_template(db, template_in, admin.id)


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int, update_in: TemplateUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)
):
    return service.update_template(db, template_id, update_in)


@router.delete("/templates/{template_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_template(db, template_id)


@router.post("/preview", response_model=PreviewResponse)
def preview(preview_in: PreviewRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.preview(db, preview_in)


@router.post("/messages", response_model=PrepareResponse, status_code=HTTPStatus.CREATED)
def prepare_message(
    prepare_in: PrepareRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return service.prepare(db, prepare_in, current_user.id)


@router.post("/messages/{message_id}/decision", response_model=MessageResponse)
def decide_message(
    message_id: int,
    decision_in: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.decide(db, message_id, decision_in, current_user)


@router.get("/messages", response_model=MessageListResponse)
def list_messages(
    business_id: Optional[int] = Query(None),
    mine: bool = Query(False),
    status: Optional[MessageStatus] = Query(None),
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.list_messages(
        db, business_id=business_id, mine_id=current_user.id if mine else None, status=status, page=page, limit=limit
    )
