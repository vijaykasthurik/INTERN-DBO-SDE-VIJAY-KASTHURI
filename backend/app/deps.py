"""Dependency injection providers for FastAPI routes."""

from app.config import Settings, get_settings


def get_current_settings() -> Settings:
    """Provide application settings dependency."""
    return get_settings()
