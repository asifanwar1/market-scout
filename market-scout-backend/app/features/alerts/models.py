from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class AlertKind(str, PyEnum):
    NEW_LEAD = "new_lead"
    GROWING = "growing"
    REACHABLE = "reachable"


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("kind", "business_id", "dedupe_key", name="uq_alerts_kind_business_key"),)

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    dedupe_key = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    detail = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class AlertRead(Base):
    __tablename__ = "alert_reads"

    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    read_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
