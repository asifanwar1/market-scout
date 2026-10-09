from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.constants import PERCENT_MAX, PRICE_DIGITS
from app.core.database import Base
from app.core.scouting.sources.registry import get_source_info


class RunStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_RUN_STATUSES = (RunStatus.QUEUED.value, RunStatus.RUNNING.value, RunStatus.CANCELLING.value)


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


run_geographies = Table(
    "run_geographies",
    Base.metadata,
    Column("run_id", Integer, ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True),
    Column("geography_id", Integer, ForeignKey("geographies.id", ondelete="CASCADE"), primary_key=True),
)


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile_name = Column(String, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default=RunStatus.QUEUED.value, index=True)
    source_keys = Column(JSON, nullable=False, default=list)
    segment_slugs = Column(JSON, nullable=True)
    enrich_websites = Column(Boolean, nullable=False, default=True)
    refresh = Column(Boolean, nullable=False, default=False)
    max_paid_requests = Column(Integer, nullable=True)
    paid_requests_used = Column(Integer, nullable=False, default=0)

    tasks_total = Column(Integer, nullable=False, default=0)
    tasks_done = Column(Integer, nullable=False, default=0)
    tasks_failed = Column(Integer, nullable=False, default=0)
    tasks_skipped = Column(Integer, nullable=False, default=0)
    enrich_total = Column(Integer, nullable=False, default=0)
    enrich_done = Column(Integer, nullable=False, default=0)
    stats = Column(JSON, nullable=False, default=dict)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    geographies = relationship("Geography", secondary=run_geographies)
    tasks = relationship("RunTask", back_populates="run", cascade="all, delete-orphan", order_by="RunTask.id")

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_RUN_STATUSES

    @property
    def progress_percent(self) -> int:
        if not self.tasks_total:
            return 0
        finished = self.tasks_done + self.tasks_failed + self.tasks_skipped
        return min(PERCENT_MAX, round(PERCENT_MAX * finished / self.tasks_total))

    @property
    def estimated_cost_usd(self) -> float:
        total = 0.0
        for key, values in (self.stats or {}).items():
            info = get_source_info(key)
            if info is not None and info.is_paid:
                total += values.get("requests", 0) * info.cost_per_request(settings)
        return round(total, PRICE_DIGITS)


class RunTask(Base):
    __tablename__ = "run_tasks"
    __table_args__ = (Index("ix_run_tasks_search_key", "source_key", "geography_id", "term_text"),)

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_key = Column(String, nullable=False)
    geography_id = Column(Integer, ForeignKey("geographies.id", ondelete="SET NULL"), nullable=True)
    geography_name = Column(String, nullable=False)
    search_term_id = Column(Integer, ForeignKey("profile_search_terms.id", ondelete="SET NULL"), nullable=True)
    term_text = Column(String, nullable=False)
    term_language = Column(String, nullable=False)
    segment_slug = Column(String, nullable=False)
    status = Column(String, nullable=False, default=TaskStatus.PENDING.value, index=True)
    results_count = Column(Integer, nullable=False, default=0)
    new_count = Column(Integer, nullable=False, default=0)
    requests_made = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    run = relationship("Run", back_populates="tasks")
