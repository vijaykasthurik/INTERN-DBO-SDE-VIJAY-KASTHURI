"""LLM Router managing fallback chains, circuit breakers, rate limits, and provider health."""

import asyncio
import random
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

import structlog

from app.config import Settings, get_settings
from app.llm.base import (
    LLMAuthenticationError,
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    LLMServerError,
    LLMTimeoutError,
    ToolDefinition,
)
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.openrouter import OpenRouterProvider

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Tracks provider failures and temporarily disables failing providers."""

    def __init__(self, failure_threshold: int = 3, recovery_time_sec: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = recovery_time_sec
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state: Literal["closed", "open", "half_open"] = "closed"

    def can_execute(self) -> bool:
        """Determine if a request should be attempted."""
        if self.state == "closed":
            return True
        now = time.perf_counter()
        if self.state == "open":
            if now - self.last_failure_time >= self.recovery_time_sec:
                self.state = "half_open"
                return True
            return False
        # half_open allows a single trial probe
        return True

    def record_success(self) -> None:
        """Reset state upon successful response."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        """Increment failure counter and trip breaker if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.perf_counter()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class TokenBucket:
    """Simple rate limiter implementing the token bucket algorithm."""

    def __init__(self, capacity: float = 60.0, refill_rate: float = 1.0) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.perf_counter()

    def _refill(self) -> None:
        now = time.perf_counter()
        delta = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)
        self.last_refill = now

    def consume(self, amount: float = 1.0) -> bool:
        """Attempt to consume tokens. Returns True if tokens were available."""
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    @property
    def available_tokens(self) -> float:
        self._refill()
        return round(self.tokens, 1)


class LLMRouter(LLMProvider):
    """Orchestrates primary and fallback providers with rate limiting and circuit breakers."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

        # Instantiate provider adapters
        self.providers: dict[str, LLMProvider] = {
            "mock": MockLLMProvider(),
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
            "openrouter": OpenRouterProvider(),
            "openai_compat": OpenAICompatProvider(),
        }

        # Per-provider safety state
        self.circuit_breakers: dict[str, CircuitBreaker] = {
            name: CircuitBreaker() for name in self.providers
        }
        self.rate_limiters: dict[str, TokenBucket] = {
            name: TokenBucket(capacity=60.0, refill_rate=1.0) for name in self.providers
        }

    def _resolve_fallback_order(self) -> list[str]:
        """Compute the sequence of provider attempts."""
        primary = self.settings.llm_provider
        configured_order = self.settings.fallback_providers_list

        order: list[str] = [primary]
        for p in configured_order:
            if p not in order and p in self.providers:
                order.append(p)

        if "mock" not in order:
            order.append("mock")

        return order

    def get_provider_status(self) -> dict[str, Any]:
        """Report live health, circuit breaker state, and rate limit status across all providers."""
        status_report: dict[str, Any] = {}
        for name, _provider in self.providers.items():
            cb = self.circuit_breakers[name]
            rl = self.rate_limiters[name]

            health_status = "healthy"
            if cb.state == "open":
                health_status = "tripped"
            elif cb.failure_count > 0 or cb.state == "half_open":
                health_status = "degraded"

            status_report[name] = {
                "status": health_status,
                "circuit_state": cb.state,
                "consecutive_failures": cb.failure_count,
                "available_tokens": rl.available_tokens,
                "is_primary": (name == self.settings.llm_provider),
            }
        return status_report

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Route request through fallback chain with retries and circuit breaker protection."""
        fallback_chain = self._resolve_fallback_order()
        last_error: Exception | None = None

        for provider_name in fallback_chain:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            cb = self.circuit_breakers[provider_name]
            rl = self.rate_limiters[provider_name]

            # Check circuit breaker
            if not cb.can_execute():
                logger.warning("circuit_breaker_open_skipping", provider=provider_name)
                continue

            # Check token bucket rate limiter
            if not rl.consume(1.0):
                logger.warning("rate_limit_exceeded_skipping", provider=provider_name)
                continue

            # Attempt completion with backoff + jitter for transient failures
            max_attempts = 2 if provider_name != "mock" else 1
            for attempt in range(max_attempts):
                try:
                    res = await provider.complete(
                        messages=messages,
                        tools=tools,
                        json_schema=json_schema,
                        tier=tier,
                        stream=stream,
                    )
                    cb.record_success()
                    return res

                except (LLMRateLimitError, LLMServerError, LLMTimeoutError) as e:
                    last_error = e
                    logger.warning(
                        "provider_transient_failure",
                        provider=provider_name,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt < max_attempts - 1:
                        # Exponential backoff + jitter
                        backoff = (2**attempt) * 0.1 + random.uniform(0.01, 0.05)
                        await asyncio.sleep(backoff)
                    else:
                        cb.record_failure()

                except (LLMAuthenticationError, LLMProviderError, Exception) as e:
                    last_error = e
                    logger.warning(
                        "provider_hard_failure",
                        provider=provider_name,
                        error=str(e),
                    )
                    cb.record_failure()
                    break

        raise LLMProviderError(
            f"All LLM providers in fallback chain failed. Last error: {last_error}"
        )
