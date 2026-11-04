"""LLM Router managing BYOK user keys, fallback chains, key pools, and circuit breakers."""

import asyncio
import time
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any, Literal

import structlog

from app.config import Settings, get_settings
from app.core.encryption import decrypt_api_key
from app.db.models import UserApiKey
from app.db.session import SessionLocal
from app.llm.base import (
    LLMAuthenticationError,
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    ToolDefinition,
)
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.pool import (
    GroqKeyPool,
    GroqPoolProvider,
    HuggingFaceProvider,
    ZAIProvider,
    check_and_record_shared_quota,
)

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Tracks provider failures and temporarily disables failing endpoints."""

    def __init__(self, failure_threshold: int = 3, recovery_time_sec: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = recovery_time_sec
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state: Literal["closed", "open", "half_open"] = "closed"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        now = time.perf_counter()
        if self.state == "open":
            if now - self.last_failure_time >= self.recovery_time_sec:
                self.state = "half_open"
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.perf_counter()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class TokenBucket:
    """Rate limiter implementing token bucket algorithm."""

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
    """Orchestrates BYOK keys and shared server fallback chains with rate limits and circuit breakers."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

        # Shared key pool
        self.groq_pool = GroqKeyPool()
        self.groq_pool_provider = GroqPoolProvider(self.groq_pool)
        self.zai_provider = ZAIProvider()
        self.hf_provider = HuggingFaceProvider()

        # Provider registry
        self.providers: dict[str, LLMProvider] = {
            "mock": MockLLMProvider(),
            "gemini": GeminiProvider(),
            "groq": self.groq_pool_provider,
            "zai": self.zai_provider,
            "huggingface": self.hf_provider,
            "openrouter": OpenRouterProvider(),
            "openai_compat": OpenAICompatProvider(),
        }

        # Safety state per provider
        self.circuit_breakers: dict[str, CircuitBreaker] = {
            name: CircuitBreaker() for name in self.providers
        }
        self.rate_limiters: dict[str, TokenBucket] = {
            name: TokenBucket(capacity=60.0, refill_rate=1.0) for name in self.providers
        }

    def _resolve_fallback_order(self) -> list[str]:
        """Compute the sequence of shared provider attempts."""
        configured_order = self.settings.fallback_providers_list
        order: list[str] = []
        for p in configured_order:
            if p in self.providers and p not in order:
                order.append(p)

        # Fallback guarantees
        for default_p in ["groq", "zai", "huggingface", "mock"]:
            if default_p in self.providers and default_p not in order:
                order.append(default_p)

        if self.settings.llm_provider != "mock":
            order = [self.settings.llm_provider] + [p for p in order if p not in {"mock", self.settings.llm_provider}]
        return order

    def get_provider_status(self) -> dict[str, Any]:
        """Report live health and circuit breaker status across all providers."""
        status_report: dict[str, Any] = {}
        for name in self.providers:
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

    def get_shared_status(self) -> dict[str, Any]:
        """Detailed shared key pool health (masks all keys, exposes indices and counts)."""
        return {
            "groq_pool": self.groq_pool.get_pool_status(),
            "zai_available": bool(self.settings.zai_api_key),
            "huggingface_available": bool(self.settings.hf_api_key),
        }

    def _build_user_provider(self, user_key: UserApiKey) -> LLMProvider:
        """Instantiate an ephemeral LLMProvider decrypting the user's key in-memory."""
        plaintext_key = decrypt_api_key(user_key.ciphertext)
        pid = user_key.provider_id.lower()

        if pid == "gemini":
            return GeminiProvider(api_key=plaintext_key)
        elif pid == "groq":
            return GroqProvider(api_key=plaintext_key)
        else:
            base_url = user_key.base_url or "https://api.openai.com/v1"
            return OpenAICompatProvider(
                base_url=base_url,
                api_key=plaintext_key,
                model_fast=user_key.model_fast,
                model_strong=user_key.model_strong,
            )

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
        user_id: int | None = None,
        analysis_id: str | None = None,
        user_key: UserApiKey | None = None,
        allow_shared_fallback: bool = True,
        on_provider_switch: Callable[[str, str, str], Coroutine[Any, Any, None]] | None = None,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Route request through user key first, then shared server fallback chain."""
        # 1. ATTEMPT USER'S OWN KEY (if provided and active)
        if user_key and user_key.status == "active":
            try:
                user_provider = self._build_user_provider(user_key)
                res = await user_provider.complete(
                    messages=messages,
                    tools=tools,
                    json_schema=json_schema,
                    tier=tier,
                    stream=stream,
                )
                # Success: update usage counters
                self._update_user_key_success(user_key.id)
                return res

            except (LLMAuthenticationError, LLMRateLimitError, Exception) as exc:
                new_status = "invalid" if isinstance(exc, LLMAuthenticationError) else "error"
                if "quota" in str(exc).lower() or "credit" in str(exc).lower():
                    new_status = "quota_exhausted"
                elif isinstance(exc, LLMRateLimitError):
                    new_status = "rate_limited"

                # Persist bad status
                self._update_user_key_failure(user_key.id, new_status, str(exc))

                if not allow_shared_fallback:
                    raise LLMProviderError(
                        f"Your {user_key.provider_id.title()} API key failed ({new_status}) and fallback to shared models is disabled in your Profile."
                    ) from exc

                # Notify via callback for SSE event `provider_switch`
                if on_provider_switch:
                    await on_provider_switch(
                        f"User key {user_key.provider_id} encountered {new_status}. Switching to shared server pool.",
                        user_key.provider_id,
                        "shared_groq",
                    )

        # 2. SHARED SERVER CHAIN
        if user_id:
            allowed, remaining = check_and_record_shared_quota(user_id, analysis_id)
            if not allowed:
                raise LLMRateLimitError(
                    "You have reached the free shared model quota (30 requests/hour). Connect your own API key in Profile for unlimited inquiries."
                )

        fallback_chain = self._resolve_fallback_order()
        last_error: Exception | None = None

        for provider_name in fallback_chain:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            cb = self.circuit_breakers[provider_name]
            rl = self.rate_limiters[provider_name]

            if not cb.can_execute() or not rl.consume():
                continue

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

            except Exception as exc:
                cb.record_failure()
                last_error = exc
                logger.warn("provider_attempt_failed", provider=provider_name, error=str(exc))
                await asyncio.sleep(0.05)

        raise LLMProviderError(f"All LLM providers failed: {last_error}")

    def _update_user_key_success(self, key_id: int) -> None:
        """Update last_used_at and request counter asynchronously."""
        try:
            with SessionLocal() as db:
                k = db.query(UserApiKey).filter(UserApiKey.id == key_id).first()
                if k:
                    k.last_used_at = time.time()  # type: ignore[assignment]
                    k.request_count += 1
                    db.commit()
        except Exception:
            pass

    def _update_user_key_failure(self, key_id: int, status_str: str, err: str) -> None:
        """Record error status on user key in metadata store."""
        try:
            with SessionLocal() as db:
                k = db.query(UserApiKey).filter(UserApiKey.id == key_id).first()
                if k:
                    k.status = status_str
                    k.last_error_code = err[:60]
                    db.commit()
        except Exception:
            pass
