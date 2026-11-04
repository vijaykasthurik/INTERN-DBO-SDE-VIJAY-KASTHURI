"""Database session manager and engine initialization for SQLite metadata."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base

settings = get_settings()

# Ensure directory exists for local SQLite database
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database schema tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide scoped database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
