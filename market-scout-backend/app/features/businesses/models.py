from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class LeadStatus(str, PyEnum):
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    QUOTED = "quoted"
    CUSTOMER = "customer"
    NOT_INTERESTED = "not_interested"


class ContactKind(str, PyEnum):
    PHONE = "phone"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False, index=True)
    address = Column(Text, nullable=True)
    geography_id = Column(Integer, ForeignKey("geographies.id", ondelete="SET NULL"), nullable=True, index=True)
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    website = Column(String, nullable=True)
    website_domain = Column(String, nullable=True, index=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    categories = Column(JSON, nullable=False, default=list)

    # Sales workflow
    lead_status = Column(String, nullable=False, default=LeadStatus.NEW.value, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    enriched_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    geography = relationship("Geography", back_populates="businesses")
    contact_points = relationship("ContactPoint", back_populates="business", cascade="all, delete-orphan")
    source_records = relationship("SourceRecord", back_populates="business", cascade="all, delete-orphan")
    classifications = relationship(
        "BusinessClassification", back_populates="business", cascade="all, delete-orphan"
    )


class ContactPoint(Base):
    __tablename__ = "contact_points"
    __table_args__ = (
        UniqueConstraint("business_id", "kind", "value", name="uq_contact_points_business_kind_value"),
    )

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String, nullable=False)
    # Normalised: E.164 for phone/whatsapp, lower-case for email, canonical URL for socials.
    value = Column(String, nullable=False, index=True)
    is_mobile = Column(Boolean, nullable=False, default=False)
    whatsapp_likely = Column(Boolean, nullable=False, default=False)
    # Provenance: which source reported this, and when we first saw it.
    source_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("Business", back_populates="contact_points")


class SourceRecord(Base):
    """What one source said about a business, kept whole so it can be re-processed later
    without re-fetching (and without re-paying)."""

    __tablename__ = "source_records"
    __table_args__ = (UniqueConstraint("source_key", "external_id", name="uq_source_records_source_external"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True)
    source_key = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    raw_payload = Column(JSON, nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)

    business = relationship("Business", back_populates="source_records")


class BusinessClassification(Base):
    __tablename__ = "business_classifications"
    __table_args__ = (UniqueConstraint("business_id", "profile_id", name="uq_business_classifications_business_profile"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("profile_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    score = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    business = relationship("Business", back_populates="classifications")
