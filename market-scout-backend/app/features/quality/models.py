from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import expression, func

from app.core.database import Base


class QualityTaskKind(str, PyEnum):
    CONTACT_CHECK = "contact_check"
    DUPLICATE_SCAN = "duplicate_scan"


class QualityTaskStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


ACTIVE_TASK_STATUSES = (QualityTaskStatus.QUEUED.value, QualityTaskStatus.RUNNING.value)


class DuplicateStatus(str, PyEnum):
    PENDING = "pending"
    MERGED = "merged"
    DISMISSED = "dismissed"


class DuplicateConfidence(str, PyEnum):
    LIKELY = "likely"
    POSSIBLE = "possible"


class QualityTask(Base):
    __tablename__ = "quality_tasks"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False)
    status = Column(String, nullable=False, default=QualityTaskStatus.QUEUED.value, index=True)
    business_ids = Column(JSON, nullable=True)
    refresh = Column(Boolean, nullable=False, default=False, server_default=expression.false())
    total = Column(Integer, nullable=False, default=0)
    done = Column(Integer, nullable=False, default=0)
    counts = Column(JSON, nullable=False, default=dict)
    error = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    __table_args__ = (UniqueConstraint("business_a_id", "business_b_id", name="uq_duplicate_candidates_pair"),)

    id = Column(Integer, primary_key=True, index=True)
    business_a_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    business_b_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String, nullable=False)
    similarity = Column(Integer, nullable=False, default=0)
    confidence = Column(String, nullable=False, default=DuplicateConfidence.POSSIBLE.value)
    status = Column(String, nullable=False, default=DuplicateStatus.PENDING.value, index=True)
    decided_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
