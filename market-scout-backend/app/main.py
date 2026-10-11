import logging
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.limiter import limiter
from app.features.ai import service as ai_service
from app.features.ai.router import router as ai_router
from app.features.alerts.router import router as alerts_router
from app.features.api_keys.router import router as api_keys_router
from app.features.auth.router import router as auth_router
from app.features.businesses.router import router as businesses_router
from app.features.compliance.router import router as compliance_router
from app.features.exports.router import router as exports_router
from app.features.geographies.router import router as geographies_router
from app.features.imports import service as imports_service
from app.features.imports.router import router as imports_router
from app.features.insights.router import router as insights_router
from app.features.jobs.models import JobKind
from app.features.jobs.router import router as jobs_router
from app.features.jobs.runner import job_runner
from app.features.outreach.router import router as outreach_router
from app.features.pipeline.router import router as pipeline_router
from app.features.profiles.router import router as profiles_router
from app.features.public_api.router import router as public_api_router
from app.features.quality import service as quality_service
from app.features.quality.router import router as quality_router
from app.features.runs import service as runs_service
from app.features.runs.router import router as runs_router
from app.features.schedules import service as schedules_service
from app.features.schedules.router import router as schedules_router
from app.features.sheets.router import router as sheets_router
from app.features.sources.router import router as sources_router
from app.features.users.router import router as users_router
from app.features.webhooks import delivery as webhooks_delivery
from app.features.webhooks import service as webhooks_service
from app.features.webhooks.router import router as webhooks_router

URL_LOGGING_LIBRARIES = ("httpx", "httpcore", "httpx2", "httpcore2")
WORKERS_RUNNING = "running"
WORKERS_STOPPED = "stopped"
WORKERS_DISABLED = "disabled"

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
for library in URL_LOGGING_LIBRARIES:
    logging.getLogger(library).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


JOB_HANDLERS = {
    JobKind.RUN: runs_service.JOB_HANDLER,
    JobKind.IMPORT: imports_service.JOB_HANDLER,
    JobKind.AI_BATCH: ai_service.JOB_HANDLER,
    JobKind.QUALITY: quality_service.JOB_HANDLER,
    JobKind.WEBHOOK: webhooks_delivery.JOB_HANDLER,
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.RUN_WORKER_ENABLED:
        runs_service.prepare_sources()
        job_runner.start(JOB_HANDLERS, tickers=[schedules_service.fire_due_schedules, webhooks_service.prune_if_due])
    yield
    job_runner.stop()


app = FastAPI(title="Market Scout API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=HTTPStatus.CONFLICT,
        content={"detail": "This change conflicts with existing data. Refresh and try again."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    response = JSONResponse(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(geographies_router, prefix="/api/v1/geographies", tags=["Geographies"])
app.include_router(profiles_router, prefix="/api/v1/profiles", tags=["Profiles"])
app.include_router(sources_router, prefix="/api/v1/sources", tags=["Sources"])
app.include_router(runs_router, prefix="/api/v1/runs", tags=["Runs"])
app.include_router(businesses_router, prefix="/api/v1/businesses", tags=["Businesses"])
app.include_router(compliance_router, prefix="/api/v1/compliance", tags=["Compliance"])
app.include_router(exports_router, prefix="/api/v1/exports", tags=["Exports"])
app.include_router(sheets_router, prefix="/api/v1/sheets", tags=["Google Sheets"])
app.include_router(insights_router, prefix="/api/v1/insights", tags=["Insights"])
app.include_router(imports_router, prefix="/api/v1/imports", tags=["Imports"])
app.include_router(pipeline_router, prefix="/api/v1/pipeline", tags=["Pipeline"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(schedules_router, prefix="/api/v1/schedules", tags=["Schedules"])
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(quality_router, prefix="/api/v1/quality", tags=["Quality"])
app.include_router(outreach_router, prefix="/api/v1/outreach", tags=["Outreach"])
app.include_router(api_keys_router, prefix="/api/v1/api-keys", tags=["API keys"])
app.include_router(webhooks_router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(public_api_router, prefix="/api/v1/public", tags=["Public API"])


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Market Scout API is running"}


def _workers_state() -> str:
    if not settings.RUN_WORKER_ENABLED:
        return WORKERS_DISABLED
    running = job_runner.is_running and all(job_runner.lanes_alive().values())
    return WORKERS_RUNNING if running else WORKERS_STOPPED


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: the database did not answer")
        return JSONResponse(status_code=HTTPStatus.SERVICE_UNAVAILABLE, content={"status": "unavailable", "database": "down"})
    workers = _workers_state()
    if workers == WORKERS_STOPPED:
        logger.error("Health check: the background workers are not running")
        return JSONResponse(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE, content={"status": "degraded", "database": "ok", "workers": workers}
        )
    return {"status": "ok", "database": "ok", "workers": workers}
