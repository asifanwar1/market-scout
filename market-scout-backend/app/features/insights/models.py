from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class BusinessSnapshot(Base):
    __tablename__ = "business_snapshots"
    __table_args__ = (UniqueConstraint("business_id", "run_id", name="uq_business_snapshots_business_run"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True)
    seen_at = Column(DateTime(timezone=True), nullable=False, index=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)

    business = relationship("Business")
