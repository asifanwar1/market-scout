from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class ActivityKind(str, PyEnum):
    NOTE = "note"
    CALL = "call"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    MEETING = "meeting"
    STATUS_CHANGE = "status_change"
    ASSIGNMENT = "assignment"
    TASK_COMPLETED = "task_completed"
    OUTCOME_UPDATED = "outcome_updated"
    SEGMENT_CHANGED = "segment_changed"
    MERGED = "merged"


class ManualActivityKind(str, PyEnum):
    NOTE = "note"
    CALL = "call"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    MEETING = "meeting"


class OutcomeKind(str, PyEnum):
    WON = "won"
    LOST = "lost"


class LossReason(str, PyEnum):
    PRICE = "price"
    COMPETITOR = "competitor"
    NO_NEED = "no_need"
    NO_RESPONSE = "no_response"
    BAD_CONTACT_DATA = "bad_contact_data"
    WRONG_BUSINESS = "wrong_business"
    OTHER = "other"


class LeadActivity(Base):
    __tablename__ = "lead_activities"
    __table_args__ = (Index("ix_lead_activities_business_created", "business_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String, nullable=False, index=True)
    summary = Column(Text, nullable=True)
    from_value = Column(String, nullable=True)
    to_value = Column(String, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LeadTask(Base):
    __tablename__ = "lead_tasks"
    __table_args__ = (Index("ix_lead_tasks_open_due", "completed_at", "due_on"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    due_on = Column(Date, nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LeadOutcome(Base):
    __tablename__ = "lead_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, unique=True)
    kind = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=True)
    product = Column(String, nullable=True)
    loss_reason = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=False)
    closed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
