"""FastAPI Application Factory for Lumen."""

import os
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.byok import router as byok_router
from app.api.chat import router as chat_router
from app.api.contact import router as contact_router
from app.api.dashboards import router as dashboards_router
from app.api.datasets import router as datasets_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.api.upload import router as upload_router
from app.config import get_settings
from app.core.errors import (
    LumenException,
    generic_exception_handler,
    lumen_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.db.session import init_db
from app.observability.metrics import CONTENT_TYPE_LATEST, get_latest_metrics

logger = get_logger("lumen.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(settings.log_level)
    if settings.app_env.lower() == "production":
        missing_vars = []
        if not settings.secret_key or "insecure" in settings.secret_key.lower():
            missing_vars.append("SECRET_KEY")
        if not settings.key_encryption_secret or len(settings.key_encryption_secret) < 32:
            missing_vars.append("KEY_ENCRYPTION_SECRET")
        if not settings.database_url:
            missing_vars.append("DATABASE_URL")
        if not settings.admin_email:
            missing_vars.append("ADMIN_EMAIL")
        if not settings.admin_password or len(settings.admin_password) < 14:
            missing_vars.append("ADMIN_PASSWORD")
        if settings.llm_provider.lower() == "mock":
            missing_vars.append("LLM_PROVIDER")

        if missing_vars:
            logger.error(
                "Production startup preflight failed: Missing or invalid required environment variables: %s",
                ", ".join(missing_vars),
            )
            import sys
            sys.exit(1)

    init_db()
    try:
        from app.core.admin_seed import seed_admin_user
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            seed_admin_user(db)
    except Exception as exc:
        logger.warning("Admin seeding failed on startup", error=str(exc))
    logger.info("Starting Lumen backend", env=settings.app_env, provider=settings.llm_provider)
    yield
    logger.info("Shutting down Lumen backend")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Lumen: Enterprise-grade AI Data Analyst with Verifier & Evidence Ledger",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request Tracing & Timing Middleware
    @app.middleware("http")
    async def trace_and_time_middleware(request: Request, call_next):  # type: ignore
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        if request.url.path.startswith("/admin") or request.url.path.startswith("/api/v1/admin") or "admin2005" in request.url.path:
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    # Exception Handlers
    app.add_exception_handler(LumenException, lumen_exception_handler)  # type: ignore
    app.add_exception_handler(Exception, generic_exception_handler)

    # Routers
    app.include_router(contact_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(byok_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(dashboards_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(upload_router, prefix="/api/v1")
    app.include_router(datasets_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(health_router, prefix="")  # Also expose /health, /ready at root

    @app.get("/providers/status")
    async def providers_status() -> Response:
        from fastapi.responses import JSONResponse

        from app.api.admin import _llm_router

        return JSONResponse(content=_llm_router.get_provider_status())

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_latest_metrics(), media_type=CONTENT_TYPE_LATEST)

    # Mount frontend static distribution with SPA fallback
    frontend_dist_dir = os.environ.get("FRONTEND_DIST_DIR")
    if not frontend_dist_dir:
        candidates = [
            Path("/app/frontend/dist"),
            Path(__file__).resolve().parents[2] / "frontend" / "dist",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                frontend_dist_dir = str(c)
                break

    if frontend_dist_dir and os.path.exists(frontend_dist_dir):
        from fastapi.staticfiles import StaticFiles
        from starlette.responses import FileResponse, JSONResponse

        assets_path = os.path.join(frontend_dist_dir, "assets")
        if os.path.exists(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> Response:
            if (
                full_path.startswith("api/")
                or full_path in ("health", "ready", "metrics", "docs", "openapi.json")
                or full_path.startswith("providers/")
            ):
                return JSONResponse(status_code=404, content={"message": "Not Found"})

            file_path = os.path.join(frontend_dist_dir, full_path)
            if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)

            index_path = os.path.join(frontend_dist_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return JSONResponse(status_code=404, content={"message": "Not Found"})

    return app


app = create_app()
