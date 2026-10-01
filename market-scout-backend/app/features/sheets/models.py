from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.sql import func

from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
