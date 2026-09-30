from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class DataSource(Base):
    """Per-installation state of a source from the code-defined catalogue: on/off and its key."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    is_enabled = Column(Boolean, nullable=False, default=False)
    encrypted_api_key = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
