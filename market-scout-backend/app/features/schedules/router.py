from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.runs.schemas import RunResponse
from app.features.schedules import service
from app.features.schedules.schemas import ScheduleCreate, ScheduleListResponse, ScheduleResponse, ScheduleUpdate
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=ScheduleListResponse)
def list_schedules(
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_schedules(db, page=page, limit=limit)


@router.post("/", response_model=ScheduleResponse, status_code=HTTPStatus.CREATED)
def create_schedule(
    schedule_in: ScheduleCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)
):
    return service.create_schedule(db, schedule_in, created_by_id=current_admin.id)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_schedule_view(db, schedule_id)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: int, update_in: ScheduleUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)
):
    return service.update_schedule(db, schedule_id, update_in)


@router.delete("/{schedule_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    service.delete_schedule(db, schedule_id)


@router.post("/{schedule_id}/run-now", response_model=RunResponse, status_code=HTTPStatus.CREATED)
def run_schedule_now(schedule_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.run_now(db, schedule_id)
