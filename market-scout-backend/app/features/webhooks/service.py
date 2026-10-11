import ipaddress
import logging
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import FIRST_PAGE
from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.core.database import WorkerSessionLocal
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.scouting.enrichment.website import EnrichmentError, default_resolver
from app.features.jobs import service as jobs_service
from app.features.jobs.models import JobKind
from app.features.webhooks.models import (
    SUBSCRIBABLE_EVENTS,
    DeliveryStatus,
    Webhook,
    WebhookDelivery,
    WebhookEvent,
)
from app.features.webhooks.schemas import WebhookCreate, WebhookUpdate

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 20
MAX_ATTEMPTS = 5
RETRY_DELAYS_SECONDS = (30, 120, 600, 3600)
DISABLE_AFTER_FAILURES = 15
RETENTION_DAYS = 30
PRUNE_SECONDS = 3600.0
SECRET_PREFIX = "whsec_"
SECRET_BYTES = 24
SECURE_SCHEME = "https"
INSECURE_SCHEME = "http"
HOOK_NOT_FOUND_MESSAGE = "Webhook not found"
DELIVERY_NOT_FOUND_MESSAGE = "Delivery not found"
NOTHING_TO_UPDATE_MESSAGE = "Send at least one thing to change"
NEEDS_HTTPS_MESSAGE = "The address must start with https://"
NEEDS_HTTP_MESSAGE = "The address must start with http:// or https://"
NO_HOST_MESSAGE = "The address has no host name"
NO_CREDENTIALS_MESSAGE = "The address must not contain a username or password"
UNRESOLVED_MESSAGE = "Could not find {host} on the internet"
NOT_PUBLIC_MESSAGE = "{host} is not a public address"
ONLY_FAILED_RETRY_MESSAGE = "Only a delivery that failed can be sent again"
TURNED_OFF_NOTE = "Turned off after {count} failed attempts in a row"
SECRET_UNREADABLE_HINT = "…"

EVENT_INFO = {
    WebhookEvent.LEAD_CREATED: ("New lead found", "A search or import found a business that was not in the list before."),
    WebhookEvent.LEAD_STATUS_CHANGED: (
        "Lead status changed",
        "A lead moved to another status. When it becomes a customer or not interested, the deal outcome is included.",
    ),
    WebhookEvent.ALERT_RAISED: (
        "Alert raised",
        "The same signals shown on the Alerts page: a new good lead, a growing business, a newly reachable lead.",
    ),
    WebhookEvent.MESSAGE_SENT: ("Message sent", "Someone confirmed that a WhatsApp or email message to a lead was sent."),
}

resolve_host: Callable[[str], list[str]] = default_resolver
_last_prune = 0.0


def _now() -> datetime:
    return datetime.now(UTC)


def get_config() -> dict:
    return {
        "events": [{"key": event, "label": EVENT_INFO[event][0], "description": EVENT_INFO[event][1]} for event in SUBSCRIBABLE_EVENTS],
        "max_attempts": MAX_ATTEMPTS,
        "disable_after_failures": DISABLE_AFTER_FAILURES,
        "allow_private_urls": settings.WEBHOOKS_ALLOW_PRIVATE_URLS,
    }


def _shape_problem(url: str) -> str | None:
    parsed = urlparse(url)
    allowed = (SECURE_SCHEME, INSECURE_SCHEME) if settings.WEBHOOKS_ALLOW_PRIVATE_URLS else (SECURE_SCHEME,)
    if parsed.scheme not in allowed:
        return NEEDS_HTTP_MESSAGE if settings.WEBHOOKS_ALLOW_PRIVATE_URLS else NEEDS_HTTPS_MESSAGE
    if not parsed.hostname:
        return NO_HOST_MESSAGE
    if parsed.username or parsed.password:
        return NO_CREDENTIALS_MESSAGE
    return None


def public_url_problem(url: str) -> str | None:
    problem = _shape_problem(url)
    if problem is not None:
        return problem
    host = urlparse(url).hostname
    try:
        addresses = [str(ipaddress.ip_address(host))]
    except ValueError:
        try:
            addresses = resolve_host(host)
        except EnrichmentError:
            return UNRESOLVED_MESSAGE.format(host=host)
    if not addresses:
        return UNRESOLVED_MESSAGE.format(host=host)
    if settings.WEBHOOKS_ALLOW_PRIVATE_URLS:
        return None
    if not all(ipaddress.ip_address(address).is_global for address in addresses):
        return NOT_PUBLIC_MESSAGE.format(host=host)
    return None


def _require_valid_url(url: str) -> None:
    problem = public_url_problem(url)
    if problem is not None:
        raise BadRequestException(problem)


def _new_secret() -> str:
    return SECRET_PREFIX + secrets.token_urlsafe(SECRET_BYTES)


def _hint(hook: Webhook) -> str:
    plain = decrypt_secret(hook.secret)
    return mask_secret(plain) if plain else SECRET_UNREADABLE_HINT


def view(hook: Webhook) -> dict:
    return {
        "id": hook.id, "name": hook.name, "url": hook.url, "events": hook.events or [], "is_active": hook.is_active,
        "consecutive_failures": hook.consecutive_failures, "last_delivery_at": hook.last_delivery_at,
        "last_status_code": hook.last_status_code, "last_error": hook.last_error, "secret_hint": _hint(hook),
        "created_at": hook.created_at,
    }


def _get_hook(db: Session, hook_id: int) -> Webhook:
    hook = db.query(Webhook).filter(Webhook.id == hook_id).first()
    if hook is None:
        raise NotFoundException(HOOK_NOT_FOUND_MESSAGE)
    return hook


def list_webhooks(db: Session) -> dict:
    rows = db.query(Webhook).order_by(Webhook.created_at.desc(), Webhook.id.desc()).all()
    return {"data": [view(row) for row in rows], "count": len(rows)}


def create_webhook(db: Session, hook_in: WebhookCreate, actor_id: int) -> dict:
    _require_valid_url(hook_in.url)
    secret = _new_secret()
    hook = Webhook(
        name=hook_in.name, url=hook_in.url, secret=encrypt_secret(secret), events=[event.value for event in hook_in.events],
        is_active=True, created_by_id=actor_id,
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return {**view(hook), "secret": secret}


def update_webhook(db: Session, hook_id: int, update_in: WebhookUpdate) -> dict:
    hook = _get_hook(db, hook_id)
    data = update_in.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(NOTHING_TO_UPDATE_MESSAGE)
    if data.get("url") is not None and data["url"] != hook.url:
        _require_valid_url(data["url"])
        hook.url = data["url"]
    if data.get("name") is not None:
        hook.name = data["name"]
    if data.get("events") is not None:
        hook.events = [event.value for event in data["events"]]
    if data.get("is_active") is not None:
        if data["is_active"] and not hook.is_active:
            hook.consecutive_failures = 0
            hook.last_error = None
        hook.is_active = data["is_active"]
    db.commit()
    db.refresh(hook)
    return view(hook)


def rotate_secret(db: Session, hook_id: int) -> dict:
    hook = _get_hook(db, hook_id)
    secret = _new_secret()
    hook.secret = encrypt_secret(secret)
    db.commit()
    db.refresh(hook)
    return {**view(hook), "secret": secret}


def delete_webhook(db: Session, hook_id: int) -> None:
    hook = _get_hook(db, hook_id)
    db.delete(hook)
    db.commit()


def _delivery_view(delivery: WebhookDelivery) -> dict:
    waiting = delivery.status == DeliveryStatus.QUEUED.value
    return {
        "id": delivery.id, "webhook_id": delivery.webhook_id, "event": delivery.event, "status": delivery.status,
        "attempts": delivery.attempts, "next_attempt_at": delivery.next_attempt_at if waiting else None,
        "response_status": delivery.response_status, "error": delivery.error, "created_at": delivery.created_at,
        "delivered_at": delivery.delivered_at,
    }


def _queue(db: Session, hook: Webhook, event: WebhookEvent, payload: dict) -> WebhookDelivery:
    delivery = WebhookDelivery(
        webhook_id=hook.id, event=event.value, payload=payload, status=DeliveryStatus.QUEUED.value, attempts=0,
        next_attempt_at=_now(),
    )
    db.add(delivery)
    db.flush()
    jobs_service.enqueue(db, JobKind.WEBHOOK, delivery.id)
    return delivery


def emit(db: Session, event: WebhookEvent, build: Callable[[], dict]) -> int:
    hooks = [hook for hook in db.query(Webhook).filter(Webhook.is_active.is_(True)).all() if event.value in (hook.events or [])]
    if not hooks:
        return 0
    db.flush()
    payload = build()
    for hook in hooks:
        _queue(db, hook, event, payload)
    return len(hooks)


def send_test(db: Session, hook_id: int) -> dict:
    hook = _get_hook(db, hook_id)
    delivery = _queue(db, hook, WebhookEvent.PING, {"message": "This is a test from Market Scout"})
    db.commit()
    db.refresh(delivery)
    return _delivery_view(delivery)


def list_deliveries(db: Session, hook_id: int, page: int = FIRST_PAGE, limit: int = DEFAULT_LIMIT) -> dict:
    _get_hook(db, hook_id)
    query = db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == hook_id)
    total = query.count()
    rows = query.order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"data": [_delivery_view(row) for row in rows], "count": total}


def retry_delivery(db: Session, delivery_id: int) -> dict:
    delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
    if delivery is None:
        raise NotFoundException(DELIVERY_NOT_FOUND_MESSAGE)
    if delivery.status != DeliveryStatus.FAILED.value:
        raise BadRequestException(ONLY_FAILED_RETRY_MESSAGE)
    delivery.status = DeliveryStatus.QUEUED.value
    delivery.attempts = 0
    delivery.error = None
    delivery.next_attempt_at = _now()
    db.flush()
    jobs_service.enqueue(db, JobKind.WEBHOOK, delivery.id)
    db.commit()
    db.refresh(delivery)
    return _delivery_view(delivery)


def prune(db: Session) -> int:
    cutoff = _now() - timedelta(days=RETENTION_DAYS)
    removed = (
        db.query(WebhookDelivery)
        .filter(
            WebhookDelivery.status.in_((DeliveryStatus.DELIVERED.value, DeliveryStatus.FAILED.value)),
            WebhookDelivery.created_at < cutoff,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return removed


def prune_if_due() -> None:
    global _last_prune
    if time.monotonic() - _last_prune < PRUNE_SECONDS:
        return
    _last_prune = time.monotonic()
    db = WorkerSessionLocal()
    try:
        prune(db)
    except Exception:
        logger.exception("Clearing old webhook deliveries failed")
        db.rollback()
    finally:
        db.close()
