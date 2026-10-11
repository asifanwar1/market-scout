from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import expression, func

from app.core.database import Base


class ScheduleFrequency(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


FREQUENCY_DAYS = {
    ScheduleFrequency.DAILY.value: 1,
    ScheduleFrequency.WEEKLY.value: 7,
    ScheduleFrequency.MONTHLY.value: 30,
}


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile_name = Column(String, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=expression.true(), index=True)
    frequency = Column(String, nullable=False)
    geography_ids = Column(JSON, nullable=False, default=list)
    source_keys = Column(JSON, nullable=False, default=list)
    segment_slugs = Column(JSON, nullable=True)
    enrich_websites = Column(Boolean, nullable=False, default=True)
    max_paid_requests = Column(Integer, nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
