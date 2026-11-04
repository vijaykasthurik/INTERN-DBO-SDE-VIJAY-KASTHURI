"""Global pytest fixtures and hermetic environment configuration."""

import os
import shutil
import tempfile
import pytest

# Ensure hermetic testing environment with isolated temporary storage
_test_tmp_dir = tempfile.mkdtemp(prefix="lumen_test_data_")
os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATA_DIR"] = _test_tmp_dir
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
