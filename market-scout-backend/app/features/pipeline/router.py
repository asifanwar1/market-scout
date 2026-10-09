from datetime import date
from http import HTTPStatus
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.pipeline import service
from app.features.pipeline.schemas import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    PipelineConfigResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskSummaryResponse,
    TaskUpdate,
)
from app.features.pipeline.service import TaskScope
from app.features.users.models import User

router = APIRouter()


@router.get("/config", response_model=PipelineConfigResponse)
def get_config(_=Depends(get_current_user)):
    return service.get_config()


@router.get("/leads/{business_id}/activities", response_model=ActivityListResponse)
def list_activities(
    business_id: int,
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_ACTIVITY_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_activities(db, business_id, page=page, limit=limit)


@router.post("/leads/{business_id}/activities", response_model=ActivityResponse, status_code=HTTPStatus.CREATED)
def add_activity(
    business_id: int,
    activity_in: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.add_activity(db, business_id, activity_in, current_user.id)


@router.post("/leads/{business_id}/tasks", response_model=TaskResponse, status_code=HTTPStatus.CREATED)
def create_task(
    business_id: int,
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.create_task(db, business_id, task_in, current_user.id)


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    scope: TaskScope = Query(TaskScope.OPEN),
    mine: bool = Query(False, description="Only tasks assigned to me"),
    business_id: Optional[int] = Query(None),
    today: Optional[date] = Query(None, description="The caller's local date; defaults to today in UTC"),
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(service.DEFAULT_TASK_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_tasks(
        db, scope=scope, today=today, assigned_to_id=current_user.id if mine else None, business_id=business_id,
        page=page, limit=limit,
    )


@router.get("/tasks/summary", response_model=TaskSummaryResponse)
def task_summary(
    mine: bool = Query(True, description="Only tasks assigned to me"),
    today: Optional[date] = Query(None, description="The caller's local date; defaults to today in UTC"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_task_summary(db, today, current_user.id if mine else None)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.update_task(db, task_id, task_in, current_user.id)


@router.delete("/tasks/{task_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service.delete_task(db, task_id)
