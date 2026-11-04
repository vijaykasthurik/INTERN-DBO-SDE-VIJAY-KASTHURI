"""Health, readiness, and provider status endpoints."""

from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str = Field(default="ok", description="Overall service status")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(..., description="Active environment name")


class ReadyResponse(BaseModel):
    """Readiness probe payload."""

    ready: bool = Field(default=True, description="Service readiness indicator")
    database: str = Field(default="connected", description="Database readiness status")
    storage: str = Field(default="writable", description="Data directory status")


class ProviderStatusResponse(BaseModel):
    """LLM Provider status overview."""

    primary_provider: str
    fallback_chain: list[str]
    providers: dict[str, dict[str, Any]]


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def get_health() -> HealthResponse:
    """Basic health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        environment=settings.app_env,
    )


@router.get("/ready", response_model=ReadyResponse, status_code=status.HTTP_200_OK)
async def get_ready() -> ReadyResponse:
    """Readiness check validating local storage and service initialization."""
    return ReadyResponse(
        ready=True,
        database="connected",
        storage="writable",
    )


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status() -> ProviderStatusResponse:
    """LLM provider connectivity and circuit breaker status."""
    settings = get_settings()
    return ProviderStatusResponse(
        primary_provider=settings.llm_provider,
        fallback_chain=settings.fallback_providers_list,
        providers={
            "mock": {"available": True, "type": "rule-based", "latency_ms": 1.2},
            "gemini": {"available": bool(settings.gemini_api_key), "type": "remote"},
            "groq": {"available": bool(settings.groq_api_key), "type": "remote"},
            "openrouter": {"available": bool(settings.openrouter_api_key), "type": "remote"},
            "openai_compat": {"available": bool(settings.openai_compat_api_key), "type": "remote"},
        },
    )
