from http import HTTPStatus

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import BYTES_PER_MEGABYTE, FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.core.exceptions import BadRequestException
from app.features.auth.dependencies import get_current_admin_user
from app.features.imports import service
from app.features.imports.schemas import ImportListResponse, ImportOptions, ImportPreviewResponse, ImportResponse
from app.features.users.models import User

router = APIRouter()


def _read(file: UploadFile) -> bytes:
    return file.file.read(settings.IMPORT_MAX_MB * BYTES_PER_MEGABYTE + 1)


@router.post("/preview", response_model=ImportPreviewResponse)
def preview_import(file: UploadFile = File(...), _=Depends(get_current_admin_user)):
    return service.preview(file.filename or "", _read(file))


@router.post("/", response_model=ImportResponse, status_code=HTTPStatus.CREATED)
def create_import(
    file: UploadFile = File(...),
    options: str = Form(..., description="The import options as JSON"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    try:
        parsed = ImportOptions.model_validate_json(options)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        raise BadRequestException(f"{where}: {first['msg']}" if where else first["msg"]) from None
    return service.create_import(db, file.filename or "", _read(file), parsed, created_by_id=current_user.id)


@router.get("/", response_model=ImportListResponse)
def list_imports(
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_imports(db, page=page, limit=limit)


@router.get("/{import_id}", response_model=ImportResponse)
def get_import(import_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_import_by_id(db, import_id)


@router.post("/{import_id}/cancel", response_model=ImportResponse)
def cancel_import(import_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.cancel_import(db, import_id)
