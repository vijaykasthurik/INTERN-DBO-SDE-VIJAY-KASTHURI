"""Shared Server LLM Key Pool and Provider Management.

Manages:
1. Groq multi-key pool with round-robin load distribution, automatic 429 cooldown, and 401/403 filtering.
2. Z.AI (GLM-4) provider adapter.
3. Hugging Face Inference provider adapter with schema enforcement.
4. Per-user shared quota tracking (default 30 questions/hour).
"""

import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

import structlog

from app.config import get_settings
from app.llm.base import (
    LLMAuthenticationError,
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    ToolDefinition,
)
from app.llm.groq import GroqProvider
from app.llm.openai_compat import OpenAICompatProvider

logger = structlog.get_logger(__name__)

# User shared-pool hourly quota tracker: user_id -> list of request timestamps
_USER_SHARED_HOURLY_USAGE: dict[int, list[float]] = {}


def check_and_record_shared_quota(user_id: int) -> tuple[bool, int]:
    """Verify user has not exceeded hourly limit on shared server pool.

    Returns (allowed: bool, remaining_quota: int).
    """
    settings = get_settings()
    limit = settings.shared_pool_hourly_limit
    now = time.time()
    one_hour_ago = now - 3600.0

    history = _USER_SHARED_HOURLY_USAGE.get(user_id, [])
    active = [t for t in history if t > one_hour_ago]

    if len(active) >= limit:
        _USER_SHARED_HOURLY_USAGE[user_id] = active
        return False, 0

    active.append(now)
    _USER_SHARED_HOURLY_USAGE[user_id] = active
    remaining = max(0, limit - len(active))
    return True, remaining


def get_user_shared_quota_remaining(user_id: int) -> int:
    """Return number of shared pool requests left this hour for user."""
    settings = get_settings()
    limit = settings.shared_pool_hourly_limit
    now = time.time()
    one_hour_ago = now - 3600.0
    history = _USER_SHARED_HOURLY_USAGE.get(user_id, [])
    active = [t for t in history if t > one_hour_ago]
    return max(0, limit - len(active))


class GroqKeyEntry:
    def __init__(self, index: int, key: str) -> None:
        self.index = index
        self.key = key
        self.status: Literal["healthy", "cooling_down", "invalid"] = "healthy"
        self.cooldown_until: float = 0.0
        self.failure_count: int = 0
        self.request_count: int = 0

    def is_available(self) -> bool:
        if self.status == "invalid":
            return False
        if self.status == "cooling_down":
            if time.time() >= self.cooldown_until:
                self.status = "healthy"
                return True
            return False
        return True


class GroqKeyPool:
    """Round-robin key pool manager across multiple Groq API keys."""

    def __init__(self, keys: list[str] | None = None) -> None:
        settings = get_settings()
        raw_keys = keys if keys is not None else settings.groq_keys_pool
        self.entries: list[GroqKeyEntry] = [
            GroqKeyEntry(index=i + 1, key=k) for i, k in enumerate(raw_keys)
        ]
        self._current_index = 0

    def get_pool_status(self) -> list[dict[str, Any]]:
        """Return diagnostic health status per key by index (keys are strictly redacted)."""
        now = time.time()
        report = []
        for e in self.entries:
            effective_status = e.status
            if e.status == "cooling_down" and now >= e.cooldown_until:
                effective_status = "healthy"
            report.append({
                "key_label": f"Key {e.index}",
                "status": effective_status,
                "requests_served": e.request_count,
            })
        return report

    def acquire_active_key(self) -> GroqKeyEntry | None:
        """Select next available healthy Groq key in round-robin fashion."""
        if not self.entries:
            return None

        total = len(self.entries)
        for _ in range(total):
            entry = self.entries[self._current_index % total]
            self._current_index = (self._current_index + 1) % total
            if entry.is_available():
                return entry

        # If all keys cooling down, check if any can be unblocked
        now = time.time()
        for entry in self.entries:
            if entry.status != "invalid" and now >= entry.cooldown_until:
                entry.status = "healthy"
                return entry

        return None

    def record_outcome(self, entry: GroqKeyEntry, outcome: Literal["success", "rate_limited", "invalid", "error"]) -> None:
        """Update key state based on request result."""
        if outcome == "success":
            entry.status = "healthy"
            entry.failure_count = 0
            entry.request_count += 1
        elif outcome == "rate_limited":
            # Cooldown for 60 seconds
            entry.status = "cooling_down"
            entry.cooldown_until = time.time() + 60.0
            logger.warn("groq_key_rate_limited", key_index=entry.index, cooldown_seconds=60)
        elif outcome == "invalid":
            entry.status = "invalid"
            logger.error("groq_key_invalid", key_index=entry.index)
        elif outcome == "error":
            entry.failure_count += 1
            if entry.failure_count >= 3:
                entry.status = "cooling_down"
                entry.cooldown_until = time.time() + 30.0


class GroqPoolProvider(LLMProvider):
    """Groq Provider executing over the multi-key pool with automated key failover."""

    def __init__(self, pool: GroqKeyPool | None = None) -> None:
        self.pool = pool or GroqKeyPool()

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Attempt request against available Groq keys in the pool."""
        attempts = min(3, len(self.pool.entries) or 1)
        last_exc: Exception | None = None

        for _ in range(attempts):
            key_entry = self.pool.acquire_active_key()
            if not key_entry:
                raise LLMRateLimitError("All Groq server keys are currently cooling down or exhausted.")

            provider = GroqProvider(api_key=key_entry.key)
            try:
                res = await provider.complete(
                    messages=messages,
                    tools=tools,
                    json_schema=json_schema,
                    tier=tier,
                    stream=stream,
                )
                self.pool.record_outcome(key_entry, "success")
                return res
            except LLMAuthenticationError as exc:
                self.pool.record_outcome(key_entry, "invalid")
                last_exc = exc
            except LLMRateLimitError as exc:
                self.pool.record_outcome(key_entry, "rate_limited")
                last_exc = exc
            except Exception as exc:
                self.pool.record_outcome(key_entry, "error")
                last_exc = exc

        raise last_exc or LLMProviderError("Groq pool request failed after multiple key attempts.")


class ZAIProvider(OpenAICompatProvider):
    """Z.AI (BigModel GLM-4) REST adapter."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        key = api_key or settings.zai_api_key or "dummy_zai_key"
        target_model = model or settings.zai_model or "glm-4"
        super().__init__(
            base_url="https://open.bigmodel.cn/api/paas/v4",
            api_key=key,
            model_fast="glm-4-flash",
            model_strong=target_model,
        )


class HuggingFaceProvider(OpenAICompatProvider):
    """Hugging Face Inference API adapter using OpenAI-compatible endpoints."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        key = api_key or settings.hf_api_key or "dummy_hf_key"
        model_id = model or settings.hf_model or "Qwen/Qwen2.5-7B-Instruct"
        super().__init__(
            base_url="https://router.huggingface.co/v1",
            api_key=key,
            model_fast=model_id,
            model_strong=model_id,
        )
