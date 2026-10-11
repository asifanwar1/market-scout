from fastapi import Depends, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.features.api_keys import service
from app.features.api_keys.models import ApiKey

API_KEY_HEADER = "X-API-Key"
BEARER_PREFIX = "bearer "
AUTHORIZATION_HEADER = "authorization"
READ_ONLY_MESSAGE = "This API key is read-only"

api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def read_token(request: Request, header_value: str | None = None) -> str | None:
    if header_value:
        return header_value.strip()
    authorization = request.headers.get(AUTHORIZATION_HEADER, "")
    if authorization.lower().startswith(BEARER_PREFIX):
        return authorization[len(BEARER_PREFIX):].strip()
    return None


def rate_limit_key(request: Request) -> str:
    token = read_token(request, request.headers.get(API_KEY_HEADER))
    if token:
        return service.hash_token(token)
    return request.client.host if request.client else "unknown"


def get_api_key(
    request: Request, header_value: str | None = Depends(api_key_header), db: Session = Depends(get_db)
) -> ApiKey:
    token = read_token(request, header_value)
    key = service.find_active_key(db, token) if token else None
    if key is None:
        raise UnauthorizedException()
    service.touch(db, key)
    return key


def get_writable_api_key(key: ApiKey = Depends(get_api_key)) -> ApiKey:
    if not key.can_write:
        raise ForbiddenException(READ_ONLY_MESSAGE)
    return key
