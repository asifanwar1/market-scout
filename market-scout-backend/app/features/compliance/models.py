from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class DoNotContact(Base):
    __tablename__ = "do_not_contact"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True, index=True)
    phone = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
