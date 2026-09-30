from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.runs import service
from app.features.runs.models import RunStatus, TaskStatus
from app.features.runs.schemas import (
    RunCreate, RunEstimateResponse, RunListResponse, RunResponse, RunTaskListResponse,
)
from app.features.users.models import User

router = APIRouter()


@router.get("/", response_model=RunListResponse)
def list_runs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[RunStatus] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_runs(db, page=page, limit=limit, status=status)


@router.post("/", response_model=RunResponse, status_code=201)
def create_run(run_in: RunCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)):
    return service.create_run(db, run_in, created_by_id=current_admin.id)


@router.post("/estimate", response_model=RunEstimateResponse)
def estimate_run(run_in: RunCreate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.estimate_run(db, run_in)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_run_by_id(db, run_id)


@router.get("/{run_id}/tasks", response_model=RunTaskListResponse)
def list_run_tasks(
    run_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[TaskStatus] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return service.get_run_tasks(db, run_id, page=page, limit=limit, status=status)


@router.post("/{run_id}/cancel", response_model=RunResponse)
def cancel_run(run_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.cancel_run(db, run_id)


@router.post("/{run_id}/resume", response_model=RunResponse)
def resume_run(run_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.resume_run(db, run_id)
