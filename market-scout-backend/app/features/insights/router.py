from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import LIMIT_MIN
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.insights import service
from app.features.insights.schemas import (
    Bucket,
    ConversionGroup,
    ConversionResponse,
    CoverageResponse,
    GapsResponse,
    MoversResponse,
    OverviewResponse,
    PipelineResponse,
    SourcesResponse,
    TimelineResponse,
)

DEFAULT_GAP_THRESHOLD = 5
GAP_THRESHOLD_MAX = 1000
DEFAULT_TIMELINE_DAYS = 90
TIMELINE_DAYS_MIN = 7
TIMELINE_DAYS_MAX = 730
DEFAULT_MOVERS_DAYS = 30
MOVERS_DAYS_MAX = 365
DEFAULT_MOVERS_LIMIT = 10
MOVERS_LIMIT_MAX = 50


router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def overview(profile_id: Optional[int] = Query(None), db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_overview(db, profile_id)


@router.get("/coverage", response_model=CoverageResponse)
def coverage(profile_id: int = Query(...), db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_coverage(db, profile_id)


@router.get("/gaps", response_model=GapsResponse)
def gaps(
    profile_id: int = Query(...),
    threshold: int = Query(DEFAULT_GAP_THRESHOLD, ge=1, le=GAP_THRESHOLD_MAX, description="Cities with fewer leads than this are gaps"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_gaps(db, profile_id, threshold)


@router.get("/timeline", response_model=TimelineResponse)
def timeline(
    profile_id: Optional[int] = Query(None),
    days: int = Query(DEFAULT_TIMELINE_DAYS, ge=TIMELINE_DAYS_MIN, le=TIMELINE_DAYS_MAX),
    bucket: Bucket = Query(Bucket.WEEK),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_timeline(db, profile_id, days, bucket)


@router.get("/sources", response_model=SourcesResponse)
def sources(profile_id: Optional[int] = Query(None), db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_sources(db, profile_id)


@router.get("/movers", response_model=MoversResponse)
def movers(
    profile_id: Optional[int] = Query(None),
    days: int = Query(DEFAULT_MOVERS_DAYS, ge=1, le=MOVERS_DAYS_MAX),
    limit: int = Query(DEFAULT_MOVERS_LIMIT, ge=LIMIT_MIN, le=MOVERS_LIMIT_MAX),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_movers(db, profile_id, days, limit)


@router.get("/pipeline", response_model=PipelineResponse)
def pipeline(profile_id: Optional[int] = Query(None), db: Session = Depends(get_db), _=Depends(get_current_user)):
    return service.get_pipeline(db, profile_id)


@router.get("/conversion", response_model=ConversionResponse)
def conversion(
    group_by: ConversionGroup = Query(ConversionGroup.SOURCE),
    profile_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_conversion(db, profile_id, group_by)
