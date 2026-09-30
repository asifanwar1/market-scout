import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.core.limiter import limiter
from app.features.auth.router import router as auth_router
from app.features.users.router import router as users_router
from app.features.geographies.router import router as geographies_router
from app.features.profiles.router import router as profiles_router
from app.features.sources.router import router as sources_router
from app.features.runs.router import router as runs_router
from app.features.businesses.router import router as businesses_router
from app.features.compliance.router import router as compliance_router
from app.features.runs import service as runs_service
from app.features.runs.worker import worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.RUN_WORKER_ENABLED:
        runs_service.start_worker()
    yield
    worker.stop()


app = FastAPI(title="Market Scout API", version="0.1.0", lifespan=lifespan)

# Rate-limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Added last so it's outermost -- otherwise a 429 from SlowAPIMiddleware never
# passes back through CORSMiddleware and browser clients can't read the response.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    # A constraint the service layer didn't anticipate (a duplicate slipping past validation, a
    # race). The client did something that conflicts with existing data; that isn't a server fault.
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=409,
        content={"detail": "This change conflicts with existing data. Refresh and try again."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    # Starlette runs this handler outside CORSMiddleware, so a 500 would carry no CORS headers and
    # the browser would hide it behind an opaque "Network Error". Add them for allowed origins.
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


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Market Scout API is running"}
