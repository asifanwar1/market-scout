from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, LIMIT_MAX, LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.quality import duplicates, scoring, service
from app.features.quality.models import DuplicateStatus
from app.features.quality.schemas import (
    CheckRequest,
    DuplicateListResponse,
    MergeRequest,
    MergeResponse,
    QualitySettings,
    QualitySettingsUpdate,
    QualityTaskResponse,
    ScoringApplyRequest,
    ScoringApplyResponse,
    ScoringResponse,
)
from app.features.users.models import User

router = APIRouter()


@router.post("/checks", response_model=QualityTaskResponse, status_code=HTTPStatus.CREATED)
def start_checks(check_in: CheckRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.start_checks(db, check_in, current_user.id)


@router.get("/tasks/{task_id}", response_model=QualityTaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_task(db, task_id)


@router.get("/settings", response_model=QualitySettings)
def get_settings(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_settings(db)


@router.put("/settings", response_model=QualitySettings)
def update_settings(update_in: QualitySettingsUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_settings(db, update_in)


@router.get("/duplicates", response_model=DuplicateListResponse)
def list_duplicates(
    status: DuplicateStatus = Query(DuplicateStatus.PENDING),
    page: int = Query(FIRST_PAGE, ge=FIRST_PAGE),
    limit: int = Query(duplicates.DEFAULT_LIMIT, ge=LIMIT_MIN, le=LIMIT_MAX),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin_user),
):
    return duplicates.get_duplicates(db, status=status, page=page, limit=limit)


@router.post("/duplicates/scan", response_model=QualityTaskResponse, status_code=HTTPStatus.CREATED)
def scan_duplicates(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)):
    return service.start_duplicate_scan(db, current_admin.id)


@router.post("/duplicates/{candidate_id}/merge", response_model=MergeResponse)
def merge_duplicate(
    candidate_id: int, body: MergeRequest, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)
):
    return duplicates.merge_pair(db, candidate_id, body.keep_id, current_admin.id)


@router.post("/duplicates/{candidate_id}/dismiss", status_code=HTTPStatus.NO_CONTENT)
def dismiss_duplicate(candidate_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin_user)):
    duplicates.dismiss(db, candidate_id, current_admin.id)


@router.get("/scoring", response_model=ScoringResponse)
def get_scoring(profile_id: int = Query(...), db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return scoring.analyse(db, profile_id)


@router.post("/scoring/apply", response_model=ScoringApplyResponse)
def apply_scoring(body: ScoringApplyRequest, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return scoring.apply_suggestion(db, body.profile_id)


@router.post("/scoring/revert", response_model=ScoringApplyResponse)
def revert_scoring(body: ScoringApplyRequest, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return scoring.revert(db, body.profile_id)
