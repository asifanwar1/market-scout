from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class AnalysisStatus(str, PyEnum):
    OK = "ok"
    NO_TEXT = "no_text"
    DECLINED = "declined"
    FAILED = "failed"


class BatchStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


ACTIVE_BATCH_STATUSES = (BatchStatus.QUEUED.value, BatchStatus.RUNNING.value)


class LeadAiResult(Base):
    __tablename__ = "lead_ai_results"
    __table_args__ = (UniqueConstraint("business_id", "profile_id", name="uq_lead_ai_results_business_profile"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    segment_slug = Column(String, nullable=True)
    segment_reason = Column(Text, nullable=True)
    fit_score = Column(Integer, nullable=True, index=True)
    fit_reason = Column(Text, nullable=True)
    confidence = Column(String, nullable=True)
    model = Column(String, nullable=True)
    pages_read = Column(Integer, nullable=False, default=0)
    truncated = Column(Boolean, nullable=False, default=False)
    error = Column(Text, nullable=True)
    analyzed_at = Column(DateTime(timezone=True), nullable=False)
    analyzed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class AiBatch(Base):
    __tablename__ = "ai_batches"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default=BatchStatus.QUEUED.value, index=True)
    business_ids = Column(JSON, nullable=False, default=list)
    refresh = Column(Boolean, nullable=False, default=False)
    total = Column(Integer, nullable=False, default=0)
    done = Column(Integer, nullable=False, default=0)
    analyzed = Column(Integer, nullable=False, default=0)
    skipped = Column(Integer, nullable=False, default=0)
    declined = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    spent_usd = Column(Float, nullable=False, default=0.0)
    error = Column(Text, nullable=True)
    error_samples = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
