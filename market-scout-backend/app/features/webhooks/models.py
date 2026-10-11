from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class WebhookEvent(str, PyEnum):
    LEAD_CREATED = "lead.created"
    LEAD_STATUS_CHANGED = "lead.status_changed"
    ALERT_RAISED = "alert.raised"
    MESSAGE_SENT = "message.sent"
    PING = "ping"


SUBSCRIBABLE_EVENTS = (
    WebhookEvent.LEAD_CREATED,
    WebhookEvent.LEAD_STATUS_CHANGED,
    WebhookEvent.ALERT_RAISED,
    WebhookEvent.MESSAGE_SENT,
)


class DeliveryStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DELIVERED = "delivered"
    FAILED = "failed"


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=False)
    events = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    last_status_code = Column(Integer, nullable=True)
    last_error = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_hook_created", "webhook_id", "created_at"),
        Index("ix_webhook_deliveries_due", "status", "next_attempt_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)
    event = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default=DeliveryStatus.QUEUED.value)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False)
    response_status = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
