"""Global pytest fixtures and environment configuration."""

import os

# Set testing environment variables
os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
