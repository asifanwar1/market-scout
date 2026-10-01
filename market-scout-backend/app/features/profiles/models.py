from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TermLanguage(str, PyEnum):
    EN = "en"
    UR_ROMAN = "ur-roman"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    scoring_config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    segments = relationship(
        "ProfileSegment",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileSegment.sort_order, ProfileSegment.id",
    )
    search_terms = relationship(
        "ProfileSearchTerm",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileSearchTerm.id",
    )

    @property
    def segment_count(self) -> int:
        return len(self.segments)

    @property
    def term_count(self) -> int:
        return len(self.search_terms)


class ProfileSegment(Base):
    __tablename__ = "profile_segments"
    __table_args__ = (UniqueConstraint("profile_id", "slug", name="uq_profile_segments_profile_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    match_rules = Column(JSON, nullable=False, default=dict)
    sort_order = Column(Integer, nullable=False, default=0)

    profile = relationship("Profile", back_populates="segments")
    search_terms = relationship("ProfileSearchTerm", back_populates="segment", cascade="all, delete-orphan")


class ProfileSearchTerm(Base):
    __tablename__ = "profile_search_terms"
    __table_args__ = (
        UniqueConstraint("segment_id", "text", "language", name="uq_profile_search_terms_segment_text_language"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("profile_segments.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(String, nullable=False)
    osm_filter = Column(JSON, nullable=True)
    language = Column(String, nullable=False, default=TermLanguage.EN.value)
    is_active = Column(Boolean, nullable=False, default=True)

    profile = relationship("Profile", back_populates="search_terms")
    segment = relationship("ProfileSegment", back_populates="search_terms")

    @property
    def segment_slug(self) -> str:
        return self.segment.slug
