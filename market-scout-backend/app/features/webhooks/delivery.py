import hashlib
import hmac
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import httpx
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret
from app.core.database import WorkerSessionLocal
from app.features.jobs.handler import JobHandler
from app.features.webhooks import service
from app.features.webhooks.models import DeliveryStatus, Webhook, WebhookDelivery, WebhookEvent

logger = logging.getLogger(__name__)

SEND_TIMEOUT_SECONDS = 10.0
ERROR_MAX_LENGTH = 300
USER_AGENT = "MarketScout-Webhooks/1.0"
EVENT_HEADER = "X-MarketScout-Event"
DELIVERY_HEADER = "X-MarketScout-Delivery"
SIGNATURE_HEADER = "X-MarketScout-Signature"
CONTENT_TYPE_HEADER = "Content-Type"
JSON_CONTENT_TYPE = "application/json"
SIGNATURE_FORMAT = "t={timestamp},v1={digest}"
HTTP_ERROR_FORMAT = "HTTP {status}"
REQUEST_FAILED_FORMAT = "The request failed ({reason})"
UNEXPECTED_MESSAGE = "Unexpected error (see the server log)"
INTERRUPTED_MESSAGE = "Interrupted (the server stopped); not sent again"
TURNED_OFF_MESSAGE = "The webhook was turned off"
NO_SECRET_MESSAGE = "The signing secret could not be read"


@dataclass(frozen=True)
class SendResult:
    status_code: int | None
    error: str | None


Sender = Callable[[str, dict[str, str], bytes], SendResult]


def _now() -> datetime:
    return datetime.now(UTC)


def sign(secret: str, timestamp: int, body: bytes) -> str:
    message = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return SIGNATURE_FORMAT.format(timestamp=timestamp, digest=digest)


def send_request(url: str, headers: dict[str, str], body: bytes) -> SendResult:
    problem = service.public_url_problem(url)
    if problem is not None:
        return SendResult(None, problem)
    try:
        response = httpx.post(url, content=body, headers=headers, timeout=SEND_TIMEOUT_SECONDS, follow_redirects=False)
    except httpx.HTTPError as exc:
        return SendResult(None, REQUEST_FAILED_FORMAT.format(reason=exc.__class__.__name__))
    if HTTPStatus.OK <= response.status_code < HTTPStatus.MULTIPLE_CHOICES:
        return SendResult(response.status_code, None)
    return SendResult(response.status_code, HTTP_ERROR_FORMAT.format(status=response.status_code))


def build_body(delivery: WebhookDelivery) -> bytes:
    created = delivery.created_at.isoformat() if delivery.created_at is not None else _now().isoformat()
    envelope = {"id": delivery.id, "event": delivery.event, "created_at": created, "data": delivery.payload}
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _limit_for(delivery: WebhookDelivery) -> int:
    return 1 if delivery.event == WebhookEvent.PING.value else service.MAX_ATTEMPTS


def _give_up(delivery: WebhookDelivery, error: str, now: datetime) -> None:
    delivery.status = DeliveryStatus.FAILED.value
    delivery.error = error[:ERROR_MAX_LENGTH]
    delivery.delivered_at = None
    delivery.next_attempt_at = now


def _note_result(hook: Webhook, delivery: WebhookDelivery, result: SendResult, now: datetime) -> None:
    hook.last_delivery_at = now
    hook.last_status_code = result.status_code
    hook.last_error = None if result.error is None else result.error[:ERROR_MAX_LENGTH]
    if delivery.event == WebhookEvent.PING.value:
        return
    if result.error is None:
        hook.consecutive_failures = 0
        return
    hook.consecutive_failures = (hook.consecutive_failures or 0) + 1
    if hook.consecutive_failures >= service.DISABLE_AFTER_FAILURES and hook.is_active:
        hook.is_active = False
        hook.last_error = service.TURNED_OFF_NOTE.format(count=hook.consecutive_failures)


def attempt(db: Session, delivery_id: int, sender: Sender | None = None, now: datetime | None = None) -> WebhookDelivery | None:
    delivery = db.get(WebhookDelivery, delivery_id, populate_existing=True)
    if delivery is None or delivery.status != DeliveryStatus.QUEUED.value:
        return delivery
    now = now or _now()
    hook = db.get(Webhook, delivery.webhook_id)
    if hook is None:
        return delivery

    is_ping = delivery.event == WebhookEvent.PING.value
    if not hook.is_active and not is_ping:
        _give_up(delivery, TURNED_OFF_MESSAGE, now)
        db.commit()
        return delivery

    delivery.status = DeliveryStatus.RUNNING.value
    delivery.attempts = (delivery.attempts or 0) + 1
    db.commit()

    secret = decrypt_secret(hook.secret)
    if secret is None:
        _give_up(delivery, NO_SECRET_MESSAGE, now)
        db.commit()
        return delivery

    body = build_body(delivery)
    timestamp = int(now.timestamp())
    headers = {
        CONTENT_TYPE_HEADER: JSON_CONTENT_TYPE,
        "User-Agent": USER_AGENT,
        EVENT_HEADER: delivery.event,
        DELIVERY_HEADER: str(delivery.id),
        SIGNATURE_HEADER: sign(secret, timestamp, body),
    }
    result = (sender or send_request)(hook.url, headers, body)

    finished = _now()
    delivery.response_status = result.status_code
    if result.error is None:
        delivery.status = DeliveryStatus.DELIVERED.value
        delivery.delivered_at = finished
        delivery.error = None
    elif delivery.attempts >= _limit_for(delivery):
        _give_up(delivery, result.error, finished)
    else:
        delay = service.RETRY_DELAYS_SECONDS[min(delivery.attempts, len(service.RETRY_DELAYS_SECONDS)) - 1]
        delivery.status = DeliveryStatus.QUEUED.value
        delivery.error = result.error[:ERROR_MAX_LENGTH]
        delivery.next_attempt_at = finished + timedelta(seconds=delay)
    _note_result(hook, delivery, result, finished)
    db.commit()
    return delivery


def deliver_in_new_session(delivery_id: int) -> None:
    db = WorkerSessionLocal()
    try:
        attempt(db, delivery_id)
    except Exception:
        logger.exception("Webhook delivery %s failed", delivery_id)
        db.rollback()
        delivery = db.get(WebhookDelivery, delivery_id, populate_existing=True)
        if delivery is not None and delivery.status == DeliveryStatus.RUNNING.value:
            _give_up(delivery, UNEXPECTED_MESSAGE, _now())
            db.commit()
    finally:
        db.close()


def recover_delivery(db: Session, delivery_id: int, retries_left: bool) -> bool:
    delivery = db.get(WebhookDelivery, delivery_id, populate_existing=True)
    if delivery is None or delivery.status != DeliveryStatus.RUNNING.value:
        return False
    if retries_left:
        delivery.status = DeliveryStatus.QUEUED.value
        delivery.next_attempt_at = _now()
        db.commit()
        return True
    _give_up(delivery, INTERRUPTED_MESSAGE, _now())
    db.commit()
    return False


def _queued_ids(db: Session) -> list[int]:
    query = (
        db.query(WebhookDelivery.id)
        .filter(WebhookDelivery.status == DeliveryStatus.QUEUED.value, WebhookDelivery.next_attempt_at <= _now())
        .order_by(WebhookDelivery.next_attempt_at, WebhookDelivery.id)
    )
    return [row[0] for row in query]


def _running_ids(db: Session) -> list[int]:
    query = db.query(WebhookDelivery.id).filter(WebhookDelivery.status == DeliveryStatus.RUNNING.value).order_by(WebhookDelivery.id)
    return [row[0] for row in query]


JOB_HANDLER = JobHandler(
    execute=deliver_in_new_session, recover=recover_delivery, queued_ids=_queued_ids, running_ids=_running_ids
)
