from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.sql import func

from app.database import Base


class AppSetting(Base):
    """Small installation-wide settings that don't deserve a table each (the Google Sheet link
    and its sync status today). One row per key, the value is a JSON object."""

    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
