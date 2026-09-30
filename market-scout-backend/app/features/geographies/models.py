from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class GeographyLevel(str, PyEnum):
    COUNTRY = "country"
    PROVINCE = "province"
    CITY = "city"


class Geography(Base):
    __tablename__ = "geographies"
    __table_args__ = (UniqueConstraint("parent_id", "name", name="uq_geographies_parent_name"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    level = Column(String, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("geographies.id"), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_km = Column(Float, nullable=True)
    bbox = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    parent = relationship("Geography", remote_side=[id], back_populates="children")
    children = relationship("Geography", back_populates="parent")
    businesses = relationship("Business", back_populates="geography")
