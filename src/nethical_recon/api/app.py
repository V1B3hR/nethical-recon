"""FastAPI application factory."""

from datetime import datetime, timezone

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import APIConfig
from .models import HealthResponse
from .routers import auth_router, findings_router, jobs_router, reports_router, runs_router, targets_router


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = APIConfig.from_env()

    app = FastAPI(
        title=config.title,
        description=config.description,
        version=config.version,
        docs_url=f"{config.api_prefix}/docs",
        redoc_url=f"{config.api_prefix}/redoc",
        openapi_url=f"{config.api_prefix}/openapi.json",
    )

    # CORS middleware
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=config.cors_allow_credentials,
            allow_methods=config.cors_allow_methods or ["*"],
            allow_headers=config.cors_allow_headers or ["*"],
        )

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        """Health check endpoint."""
        from nethical_recon.core.storage import get_database

        # Check database connection
        db_status = "healthy"
        try:
            db = get_database()
            with db.session():
                pass
        except Exception:
            db_status = "unhealthy"

        # Check worker connection (simplified check)
        worker_status = "unknown"
        try:
            from celery import Celery

            from nethical_recon.worker.config import WorkerConfig

            worker_config = WorkerConfig.from_env()
            celery_app = Celery(broker=worker_config.broker_url, backend=worker_config.result_backend)
            # Simple ping to check if broker is reachable
            celery_app.control.inspect().stats()
            worker_status = "healthy"
        except Exception:
            worker_status = "unhealthy"

        overall_status = "healthy" if db_status == "healthy" and worker_status == "healthy" else "degraded"

        return HealthResponse(
            status=overall_status,
            version=config.version,
            timestamp=datetime.now(timezone.utc),
            database=db_status,
            worker=worker_status,
        )

    # Version endpoint
    @app.get("/version", tags=["health"])
    async def version():
        """Get API version."""
        return {"version": config.version, "api_prefix": config.api_prefix}

    # Register routers with API prefix
    app.include_router(auth_router, prefix=config.api_prefix)
    app.include_router(targets_router, prefix=config.api_prefix)
    app.include_router(jobs_router, prefix=config.api_prefix)
    app.include_router(runs_router, prefix=config.api_prefix)
    app.include_router(findings_router, prefix=config.api_prefix)
    app.include_router(reports_router, prefix=config.api_prefix)

    # Exception handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    return app
