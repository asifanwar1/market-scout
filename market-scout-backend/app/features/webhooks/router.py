from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.users.models import User
from app.features.webhooks import service
from app.features.webhooks.schemas import (
    DeliveryListResponse,
    DeliveryResponse,
    WebhookConfigResponse,
    WebhookCreate,
    WebhookCreatedResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdate,
)

router = APIRouter()


@router.get("/config", response_model=WebhookConfigResponse)
def get_config(_=Depends(get_current_admin_user)):
    return service.get_config()


@router.get("/", response_model=WebhookListResponse)
def list_webhooks(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.list_webhooks(db)


@router.post("/", response_model=WebhookCreatedResponse, status_code=HTTPStatus.CREATED)
def create_webhook(hook_in: WebhookCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin_user)):
    return service.create_webhook(db, hook_in, admin.id)


@router.patch("/{hook_id}", response_model=WebhookResponse)
def update_webhook(hook_id: int, update_in: WebhookUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_webhook(db, hook_id, update_in)


@router.delete("/{hook_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_webhook(hook_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_webhook(db, hook_id)


@router.post("/{hook_id}/rotate-secret", response_model=WebhookCreatedResponse)
def rotate_secret(hook_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.rotate_secret(db, hook_id)


@router.post("/{hook_id}/test", response_model=DeliveryResponse, status_code=HTTPStatus.ACCEPTED)
def send_test(hook_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.send_test(db, hook_id)


@router.get("/{hook_id}/deliveries", response_model=DeliveryListResponse)
def list_deliveries(
    hook_id: int,
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.list_deliveries(db, hook_id, page=page, limit=limit)


@router.post("/deliveries/{delivery_id}/retry", response_model=DeliveryResponse, status_code=HTTPStatus.ACCEPTED)
def retry_delivery(delivery_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.retry_delivery(db, delivery_id)
