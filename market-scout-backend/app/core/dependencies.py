from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, WriteSessionLocal

_READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_db(request: Request) -> Generator[Session, None, None]:
    factory = SessionLocal if request.method in _READ_ONLY_METHODS else WriteSessionLocal
    db = factory()
    try:
        yield db
    finally:
        db.close()
