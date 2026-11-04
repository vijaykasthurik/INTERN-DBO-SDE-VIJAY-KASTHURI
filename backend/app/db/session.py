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
    if "sqlite" in settings.database_url:
        with engine.begin() as conn:
            user_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
            if user_columns and "allow_shared_fallback" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN allow_shared_fallback BOOLEAN DEFAULT 1"))
            dataset_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(datasets)"))]
            if dataset_columns and "source_filename" not in dataset_columns:
                conn.execute(text("ALTER TABLE datasets ADD COLUMN source_filename VARCHAR(255) NOT NULL DEFAULT ''"))
            report_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(report_artifacts)"))]
            if report_columns and "source_dataset_ids" not in report_columns:
                conn.execute(text("ALTER TABLE report_artifacts ADD COLUMN source_dataset_ids JSON NOT NULL DEFAULT '[]'"))


def get_db() -> Generator[Session, None, None]:
    """Provide scoped database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
