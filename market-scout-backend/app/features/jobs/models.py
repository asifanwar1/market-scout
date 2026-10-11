from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class JobKind(str, PyEnum):
    RUN = "run"
    IMPORT = "import"
    AI_BATCH = "ai_batch"
    QUALITY = "quality"
    WEBHOOK = "webhook"


class JobStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


ACTIVE_JOB_STATUSES = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_pick", "kind", "status", "run_after"),
        Index("ix_jobs_ref", "kind", "ref_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String, nullable=False)
    ref_id = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default=JobStatus.QUEUED.value, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    run_after = Column(DateTime(timezone=True), nullable=False)
    claimed_by = Column(String, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
