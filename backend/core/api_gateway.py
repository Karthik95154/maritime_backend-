import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
from fastapi import APIRouter

# Import settings and logger
from config import settings
from services.pipeline_logger import log_pipeline_error

# Import all routers
from routes.batch_reports import router as batch_reports_router
from routes.inspections import router as inspections_router
from routes.predict import router as predict_router
from routes.pipeline_trace import router as pipeline_trace_router
from routes.progress import router as progress_router
from routes.history import router as history_router
from routes.download import router as download_router
from routes.auth import router as auth_router
from routes.internal_review import router as internal_review_router
from routes.stream import router as stream_router
from routes.dashboard import router as dashboard_router
from routes.app_events import router as app_events_router
from routes.storage import router as storage_router
from routes.orchestration import router as orchestration_router
from routes.vessels import router as vessels_router
from routes.defects import router as defects_router
from routes import assets

limiter = Limiter(key_func=get_remote_address)

def setup_api_gateway(app: FastAPI):
    # Setup Rate Limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Setup Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://localhost:80", "http://localhost:5173", "https://yourproductiondomain.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "*"])
    
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        if request.url.path.startswith("/outputs") or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
            return await call_next(request)

        started_at = time.perf_counter()
        client_ip = request.client.host if request.client else "Unknown"
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            duration_sec = round(duration_ms / 1000, 3)
            logger.info(f"🟢 [{request.method}] {request.url.path} | IP: {client_ip} | Status: {response.status_code} | Time: {duration_sec}s")
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            duration_sec = round(duration_ms / 1000, 3)
            logger.error(f"🔴 [{request.method}] {request.url.path} | IP: {client_ip} | FAILED | Time: {duration_sec}s | Error: {str(exc)}")
            raise

    # Centralized Exception Handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.url}: {exc}")
        log_pipeline_error(None, "api", "unhandled exception", url=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected internal server error occurred. Please try again later."},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP exception on {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    # Register Routers
    api_router = APIRouter(prefix=settings.api_v1_str)

    api_router.include_router(predict_router)
    api_router.include_router(progress_router)
    api_router.include_router(pipeline_trace_router)
    api_router.include_router(stream_router)
    api_router.include_router(download_router)
    api_router.include_router(auth_router)
    api_router.include_router(app_events_router)
    api_router.include_router(history_router)
    api_router.include_router(inspections_router)
    api_router.include_router(dashboard_router)
    api_router.include_router(vessels_router, prefix="/vessels", tags=["vessels"])
    api_router.include_router(defects_router, prefix="/defects", tags=["defects"])
    api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
    api_router.include_router(internal_review_router)
    api_router.include_router(batch_reports_router, prefix="/batch_reports", tags=["batch_reports"])
    api_router.include_router(storage_router, prefix="/storage", tags=["storage"])
    api_router.include_router(orchestration_router, prefix="/orchestration", tags=["orchestration"])

    app.include_router(api_router)

    # Add health check route directly to app
    @app.get("/health")
    @limiter.limit("60/minute")
    def health_check(request: Request):
        return {"status": "ok", "version": "v1.1", "db": "async"}

    return app
