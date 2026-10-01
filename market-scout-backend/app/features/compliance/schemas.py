from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

PHONE_MAX_LENGTH = 40
REASON_MAX_LENGTH = 500



class DoNotContactCreate(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=PHONE_MAX_LENGTH)
    email: Optional[EmailStr] = None
    reason: Optional[str] = Field(default=None, max_length=REASON_MAX_LENGTH)

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "DoNotContactCreate":
        if (self.phone is None) == (self.email is None):
            raise ValueError("Provide either a phone number or an email address")
        return self


class BusinessDoNotContactCreate(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=REASON_MAX_LENGTH)


class DoNotContactResponse(BaseModel):
    id: int
    kind: Literal["business", "phone", "email"]
    value: str
    business_id: Optional[int] = None
    identifiers: list[str] = Field(default_factory=list)
    reason: Optional[str] = None
    added_by_id: Optional[int] = None
    created_at: datetime


class DoNotContactListResponse(BaseModel):
    data: list[DoNotContactResponse]
    count: int
