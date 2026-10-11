from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.features.auth.dependencies import get_current_admin_user
from app.features.jobs import service
from app.features.jobs.runner import job_runner
from app.features.jobs.schemas import JobsStatusResponse

router = APIRouter()


@router.get("/status", response_model=JobsStatusResponse)
def get_status(db: Session = Depends(get_db), _=Depends(get_current_admin_user)):
    return {
        "workers_enabled": settings.RUN_WORKER_ENABLED,
        "workers_running": job_runner.is_running and all(job_runner.lanes_alive().values()),
        **service.get_status(db),
    }
