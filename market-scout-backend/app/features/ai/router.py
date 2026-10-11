from http import HTTPStatus

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.features.ai import service
from app.features.ai.schemas import (
    AiResultResponse,
    AiSettingsResponse,
    AiSettingsUpdate,
    AiStatusResponse,
    AiTestResponse,
    AnalyzeRequest,
    ApplySegmentRequest,
    BatchResponse,
    EstimateRequest,
    EstimateResponse,
)
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.features.users.models import User

router = APIRouter()


@router.get("/settings", response_model=AiSettingsResponse)
def get_settings(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.get_settings(db)


@router.put("/settings", response_model=AiSettingsResponse)
def update_settings(update_in: AiSettingsUpdate, db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.update_settings(db, update_in)


@router.post("/settings/test", response_model=AiTestResponse)
def test_settings(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return service.test_key(db)


@router.get("/status", response_model=AiStatusResponse)
def get_status(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_status(db)


@router.post("/estimate", response_model=EstimateResponse)
def estimate(estimate_in: EstimateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.estimate(db, estimate_in)


@router.post("/analyze", response_model=BatchResponse, status_code=HTTPStatus.CREATED)
def analyze(
    analyze_in: AnalyzeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return service.start_batch(db, analyze_in, current_user.id)


@router.get("/batches/{batch_id}", response_model=BatchResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_batch(db, batch_id)


@router.post("/leads/{business_id}/apply-segment", response_model=AiResultResponse)
def apply_segment(
    business_id: int,
    apply_in: ApplySegmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.apply_segment(db, business_id, apply_in.profile_id, current_user.id)
