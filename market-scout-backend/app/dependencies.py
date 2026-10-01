from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.database import SessionLocal, WriteSessionLocal

_READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_db(request: Request) -> Generator[Session, None, None]:
    # Requests that change data lock the database up front (see app/database.py); reads never wait.
    factory = SessionLocal if request.method in _READ_ONLY_METHODS else WriteSessionLocal
    db = factory()
    try:
        yield db
    finally:
        db.close()
