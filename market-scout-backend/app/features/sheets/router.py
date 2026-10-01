from http import HTTPStatus

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.sheets import service
from app.features.sheets.schemas import SheetsSettingsResponse, SheetsTestResponse, SheetsUpdate

router = APIRouter()


@router.get("/", response_model=SheetsSettingsResponse)
def get_sheets_settings(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_settings(db)


@router.put("/", response_model=SheetsSettingsResponse)
def update_sheets_settings(update_in: SheetsUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_settings(db, update_in)


@router.post("/test", response_model=SheetsTestResponse)
def test_sheets_connection(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.test_connection(db)


@router.post("/sync", response_model=SheetsSettingsResponse, status_code=HTTPStatus.ACCEPTED)
def sync_sheet(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.start_sync(db)
