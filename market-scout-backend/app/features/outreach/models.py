from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class TemplateChannel(str, PyEnum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    ANY = "any"


class MessageChannel(str, PyEnum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class MessageStatus(str, PyEnum):
    OPENED = "opened"
    SENT = "sent"
    NOT_SENT = "not_sent"


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    channel = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"
    __table_args__ = (Index("ix_outreach_messages_business_created", "business_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(Integer, ForeignKey("message_templates.id", ondelete="SET NULL"), nullable=True)
    template_name = Column(String, nullable=True)
    channel = Column(String, nullable=False)
    to_value = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
