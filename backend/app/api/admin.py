"""Administrative and diagnostic endpoints."""

from typing import Any

from fastapi import APIRouter

from app.config import get_settings
from app.llm.router import LLMRouter

router = APIRouter(prefix="/admin", tags=["admin"])
_llm_router = LLMRouter()


@router.get("/system-info")
async def get_system_info() -> dict[str, Any]:
    """Retrieve runtime environment diagnostics."""
    settings = get_settings()
    return {
        "app_env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "cache_ttl": settings.cache_ttl_seconds,
        "max_upload_mb": settings.max_upload_mb,
    }


@router.get("/providers/status")
async def get_providers_status() -> dict[str, Any]:
    """Retrieve health and circuit breaker status across all configured LLM providers."""
    return _llm_router.get_provider_status()
