"""FastAPI Application Factory for Lumen."""

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.health import router as health_router
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
    init_db()
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
        return response

    # Exception Handlers
    app.add_exception_handler(LumenException, lumen_exception_handler)  # type: ignore
    app.add_exception_handler(Exception, generic_exception_handler)

    # Routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(upload_router, prefix="/api/v1")
    app.include_router(datasets_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(health_router, prefix="")  # Also expose /health, /ready at root

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=get_latest_metrics(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
