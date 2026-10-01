from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class DoNotContact(Base):
    """A request not to be contacted.

    Blocking a business writes one row for the business itself plus one row per phone/email it
    has (all carrying its ``business_id``). The identifier rows are what keep it blocked if a
    later scrape finds the same shop as a new record with the same phone or email. A row with
    only a phone or email and no business blocks whoever owns that number/address.
    """

    __tablename__ = "do_not_contact"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True, index=True)
    # Normalised exactly like contact points: E.164 for phones, lower-case for emails.
    phone = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
