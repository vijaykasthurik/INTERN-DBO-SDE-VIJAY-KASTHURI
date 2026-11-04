"""Database session manager and engine initialization for SQLite metadata."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
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
    # Lightweight SQLite schema migration for columns added in revisions
    if "sqlite" in settings.database_url:
        try:
            with engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(users)"))
                cols = [row[1] for row in res.fetchall()]
                if cols and "allow_shared_fallback" not in cols:
                    conn.execute(
                        text("ALTER TABLE users ADD COLUMN allow_shared_fallback BOOLEAN DEFAULT 1")
                    )
                    conn.commit()
        except Exception:
            pass


def get_db() -> Generator[Session, None, None]:
    """Provide scoped database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
