from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class DoNotContactCreate(BaseModel):
    """Block a phone number or an email address (exactly one)."""

    phone: Optional[str] = Field(default=None, max_length=40)
    email: Optional[EmailStr] = None
    reason: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "DoNotContactCreate":
        if (self.phone is None) == (self.email is None):
            raise ValueError("Provide either a phone number or an email address")
        return self


class BusinessDoNotContactCreate(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class DoNotContactResponse(BaseModel):
    id: int
    kind: Literal["business", "phone", "email"]
    # The business name, phone number or email address.
    value: str
    business_id: Optional[int] = None
    # For a blocked business: its phone numbers and emails that are blocked with it.
    identifiers: list[str] = Field(default_factory=list)
    reason: Optional[str] = None
    added_by_id: Optional[int] = None
    created_at: datetime


class DoNotContactListResponse(BaseModel):
    data: list[DoNotContactResponse]
    count: int
