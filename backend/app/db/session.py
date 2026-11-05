"""Database session manager, engine initialization, and migration runners.

Supports both local SQLite and remote PostgreSQL (Neon/Supabase/Render) with
connection retries, pool tuning, prepared statement tolerance, and Postgres advisory locks.
"""

import logging
import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.normalized_database_url

# Ensure directory exists for local SQLite database
if db_url.startswith("sqlite"):
    db_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine_kwargs: dict[str, Any] = {
    "pool_pre_ping": True,
}

if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Postgres configuration: psycopg 3 + transaction pooler compatibility
    engine_kwargs.update(
        {
            "connect_args": {"prepare_threshold": None},
            "pool_size": 5,
            "max_overflow": 10,
            "pool_recycle": 300,
        }
    )

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_connection(max_retries: int = 5, initial_backoff: float = 1.0) -> bool:
    """Validate database connectivity with exponential backoff for slow remote starts."""
    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning(
                "Database connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                backoff,
            )
            if attempt == max_retries:
                logger.error("Could not establish database connection after %d attempts.", max_retries)
                raise
            time.sleep(backoff)
            backoff *= 2.0
    return False


def run_alembic_migrations() -> None:
    """Execute Alembic migrations programmatically to head revision."""
    from alembic import command
    from alembic.config import Config

    alembic_ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    if not alembic_ini_path.exists():
        # Fall back to root or parent search
        alembic_ini_path = Path(__file__).resolve().parents[3] / "alembic.ini"

    if alembic_ini_path.exists():
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.normalized_database_url)
        command.upgrade(alembic_cfg, "head")
    else:
        Base.metadata.create_all(bind=engine)


def init_db() -> None:
    """Initialize database schema tables and apply pending migrations safely."""
    check_connection()

    is_postgres = "postgres" in db_url

    if is_postgres:
        # Postgres advisory lock (arbitrary 64-bit int 84729104) to prevent migration races
        with engine.connect() as conn:
            lock_acquired = conn.execute(text("SELECT pg_try_advisory_lock(84729104)")).scalar()
            if lock_acquired:
                try:
                    run_alembic_migrations()
                finally:
                    conn.execute(text("SELECT pg_advisory_unlock(84729104)"))
            else:
                logger.info("Another process holds the migration advisory lock. Skipping migration execution.")
    else:
        try:
            run_alembic_migrations()
        except Exception as exc:
            logger.warning("Alembic upgrade encountered error on SQLite: %s. Creating metadata tables directly.", exc)
            Base.metadata.create_all(bind=engine)

        # Legacy SQLite backward compatibility patches
        with engine.begin() as conn:
            user_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
            if user_columns:
                if "allow_shared_fallback" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN allow_shared_fallback BOOLEAN DEFAULT 1"))
                if "role" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'user'"))
                if "token_version" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1"))
                if "last_login_at" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))
                if "last_seen_at" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_seen_at DATETIME"))
                if "login_count" not in user_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN login_count INTEGER NOT NULL DEFAULT 0"))

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
