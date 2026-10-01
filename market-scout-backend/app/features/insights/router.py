from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.features.auth.dependencies import get_current_user
from app.features.insights import service
from app.features.insights.schemas import (
    Bucket,
    CoverageResponse,
    GapsResponse,
    MoversResponse,
    OverviewResponse,
    SourcesResponse,
    TimelineResponse,
)

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
    threshold: int = Query(5, ge=1, le=1000, description="Cities with fewer leads than this are gaps"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_gaps(db, profile_id, threshold)


@router.get("/timeline", response_model=TimelineResponse)
def timeline(
    profile_id: Optional[int] = Query(None),
    days: int = Query(90, ge=7, le=730),
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
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return service.get_movers(db, profile_id, days, limit)
