"""Global pytest fixtures and hermetic environment configuration."""

import asyncio
import os
import shutil
import tempfile
import pytest

# Ensure hermetic testing environment with isolated temporary storage
_test_tmp_dir = tempfile.mkdtemp(prefix="lumen_test_data_")
os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATA_DIR"] = _test_tmp_dir

# Support Postgres testing via TEST_DATABASE_URL or inherited postgres DATABASE_URL
custom_db_url = os.environ.get("TEST_DATABASE_URL")
existing_db_url = os.environ.get("DATABASE_URL", "")
if not custom_db_url and (existing_db_url.startswith("postgres://") or existing_db_url.startswith("postgresql://") or existing_db_url.startswith("postgresql+psycopg://")):
    custom_db_url = existing_db_url

if custom_db_url:
    os.environ["DATABASE_URL"] = custom_db_url
else:
    os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_test_tmp_dir, 'test_metadata.db')}"

# Clear config cache so settings use the isolated test environment
try:
    from app.config import get_settings
    get_settings.cache_clear()
except ImportError:
    pass


@pytest.fixture(scope="session", autouse=True)
def clean_test_environment():
    """Ensure tests run against a pristine database and cleanup on exit."""
    yield
    shutil.rmtree(_test_tmp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_sse_app_status():
    """Prevent 'Event is bound to a different event loop' in sse-starlette under Python 3.12."""
    try:
        from sse_starlette.sse import AppStatus
        AppStatus.should_exit_event = asyncio.Event()
    except Exception:
        pass
    yield
