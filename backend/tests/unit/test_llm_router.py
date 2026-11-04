"""Unit tests for LLM Router fallback chains, circuit breakers, rate limits, and budget governor."""

import httpx
import pytest
import respx

from app.config import Settings
from app.llm.base import (
    LLMMessage,
    LLMProviderError,
    LLMResponse,
)
from app.llm.budget import BudgetGovernor
from app.llm.router import CircuitBreaker, LLMRouter, TokenBucket


@pytest.mark.asyncio
async def test_router_primary_429_fallback_to_secondary() -> None:
    """Verify that when primary provider encounters 429, router automatically falls back and succeeds."""
    settings = Settings(
        llm_provider="gemini",
        llm_fallback_order="gemini,mock",
        gemini_api_key="test-key",
    )
    router = LLMRouter(settings=settings)

    # Mock Gemini to return HTTP 429
    url = f"{router.providers['gemini'].BASE_URL}/gemini-2.0-flash:generateContent?key=test-key"
    with respx.mock:
        respx.post(url).mock(
            return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
        )

        # Complete request - router should fall back to mock
        resp = await router.complete(
            [LLMMessage(role="user", content="Which region has highest revenue?")]
        )
        assert isinstance(resp, LLMResponse)
        assert resp.provider == "mock"
        assert "$1,482,900.00" in resp.content


@pytest.mark.asyncio
async def test_router_all_providers_fail_graceful_error() -> None:
    """Verify that when every provider in fallback chain fails, a clear LLMProviderError is raised."""
    settings = Settings(
        llm_provider="groq",
        llm_fallback_order="groq",
    )
    router = LLMRouter(settings=settings)

    # Remove mock from providers map to force all configured to fail
    router.providers["mock"].complete = None  # type: ignore

    url = "https://api.groq.com/openai/v1/chat/completions"
    with respx.mock:
        respx.post(url).mock(
            return_value=httpx.Response(500, json={"error": "Internal server error"})
        )

        with pytest.raises(LLMProviderError) as exc_info:
            await router.complete([LLMMessage(role="user", content="Test prompt")])
        assert "All LLM providers in fallback chain failed" in str(exc_info.value)


def test_circuit_breaker_transitions() -> None:
    cb = CircuitBreaker(failure_threshold=3, recovery_time_sec=1.0)
    assert cb.state == "closed"
    assert cb.can_execute() is True

    # Record 2 failures -> stays closed
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "closed"
    assert cb.can_execute() is True

    # 3rd failure -> trips to open
    cb.record_failure()
    assert cb.state == "open"
    assert cb.can_execute() is False

    # Reset on success
    cb.record_success()
    assert cb.state == "closed"
    assert cb.failure_count == 0


def test_token_bucket_rate_limiter() -> None:
    bucket = TokenBucket(capacity=2.0, refill_rate=0.1)
    assert bucket.consume(1.0) is True
    assert bucket.consume(1.0) is True
    # Third immediate token consumption denied
    assert bucket.consume(1.0) is False
    assert bucket.available_tokens < 1.0


def test_router_get_provider_status() -> None:
    router = LLMRouter()
    status = router.get_provider_status()
    assert "mock" in status
    assert "gemini" in status
    assert "groq" in status
    assert status["mock"]["status"] == "healthy"
    assert status["mock"]["is_primary"] is True


def test_budget_governor() -> None:
    governor = BudgetGovernor(max_steps=3, max_tokens=1000, max_duration_sec=5.0)

    # Initial state
    exhausted, _ = governor.is_exhausted()
    assert exhausted is False
    assert governor.select_tier("aggregation") == "fast"
    assert governor.select_tier("investigation") == "strong"

    # Record steps
    governor.record_step(tokens=400)
    governor.record_step(tokens=400)
    exhausted, _ = governor.is_exhausted()
    assert exhausted is False

    # 3rd step hits step limit
    governor.record_step(tokens=200)
    exhausted, reason = governor.is_exhausted()
    assert exhausted is True
    assert "Maximum step limit reached" in str(reason)

    notice = governor.get_degradation_notice(reason)
    assert notice["partial_analysis"] is True
    assert notice["steps_completed"] == 3
