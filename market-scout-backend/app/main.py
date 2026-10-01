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
from app.features.auth.router import router as auth_router
from app.features.businesses.router import router as businesses_router
from app.features.compliance.router import router as compliance_router
from app.features.exports.router import router as exports_router
from app.features.geographies.router import router as geographies_router
from app.features.imports import service as imports_service
from app.features.imports.router import router as imports_router
from app.features.imports.worker import import_worker
from app.features.insights.router import router as insights_router
from app.features.profiles.router import router as profiles_router
from app.features.runs import service as runs_service
from app.features.runs.router import router as runs_router
from app.features.runs.worker import worker
from app.features.sheets.router import router as sheets_router
from app.features.sources.router import router as sources_router
from app.features.users.router import router as users_router

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.RUN_WORKER_ENABLED:
        runs_service.start_worker()
        imports_service.start_worker()
    yield
    worker.stop()
    import_worker.stop()


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


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Market Scout API is running"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: the database did not answer")
        return JSONResponse(status_code=HTTPStatus.SERVICE_UNAVAILABLE, content={"status": "unavailable", "database": "down"})
    return {"status": "ok", "database": "ok"}
