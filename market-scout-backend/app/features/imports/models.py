from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import expression, func

from app.core.constants import PERCENT_MAX
from app.core.database import Base


class ImportStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_IMPORT_STATUSES = (ImportStatus.QUEUED.value, ImportStatus.RUNNING.value, ImportStatus.CANCELLING.value)


class Import(Base):
    __tablename__ = "imports"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    profile_name = Column(String, nullable=False)
    segment_slug = Column(String, nullable=True)
    default_geography_id = Column(Integer, ForeignKey("geographies.id", ondelete="SET NULL"), nullable=True)
    default_geography_name = Column(String, nullable=True)
    require_contact = Column(Boolean, nullable=False, default=True)
    lookup_contacts = Column(Boolean, nullable=False, default=False, server_default=expression.false())
    mapping = Column(JSON, nullable=False, default=dict)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status = Column(String, nullable=False, default=ImportStatus.QUEUED.value, index=True)
    rows_total = Column(Integer, nullable=False, default=0)
    rows_to_import = Column(Integer, nullable=False, default=0)
    rows_done = Column(Integer, nullable=False, default=0)
    skipped = Column(JSON, nullable=False, default=dict)
    stats = Column(JSON, nullable=False, default=dict)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def source_key(self) -> str:
        return f"import:{self.label}"

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_IMPORT_STATUSES

    @property
    def progress_percent(self) -> int:
        if not self.rows_to_import:
            return PERCENT_MAX if self.status == ImportStatus.COMPLETED.value else 0
        return min(PERCENT_MAX, round(PERCENT_MAX * self.rows_done / self.rows_to_import))
