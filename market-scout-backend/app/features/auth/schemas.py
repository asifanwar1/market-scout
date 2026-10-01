from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.constants import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, TOKEN_TYPE_BEARER
from app.core.security import validate_password_strength


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = TOKEN_TYPE_BEARER


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class MessageResponse(BaseModel):
    message: str
