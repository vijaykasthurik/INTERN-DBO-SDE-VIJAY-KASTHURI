"""Abstract base classes, models, and exceptions for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMError(Exception):
    """Base exception for all LLM operations."""

    pass


class LLMProviderError(LLMError):
    """Generic error returned or raised by an LLM provider."""

    def __init__(self, message: str, provider: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class LLMRateLimitError(LLMProviderError):
    """Raised when an LLM provider returns HTTP 429 Too Many Requests."""

    pass


class LLMServerError(LLMProviderError):
    """Raised when an LLM provider returns HTTP 5xx Server Error."""

    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM provider call times out."""

    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when an LLM provider credentials are invalid (HTTP 401/403)."""

    pass


class LLMMessage(BaseModel):
    """Normalized chat message."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class ToolDefinition(BaseModel):
    """Specification of an executable function tool for the LLM."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    """Native function call issued by an LLM."""

    id: str
    function_name: str
    arguments: dict[str, Any]


class LLMResponse(BaseModel):
    """Standardized completion output from any LLM provider."""

    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    provider: str = ""
    model: str = ""


# Cost reference per million tokens (USD): (prompt_cost, completion_cost)
PRICING_TABLE: dict[str, tuple[float, float]] = {
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-thinking-exp-01-21": (0.00, 0.00),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "google/gemini-2.0-flash-001": (0.10, 0.40),
    "anthropic/claude-3.5-sonnet": (3.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "mock": (0.00, 0.00),
}


def calculate_cost_usd(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Compute estimated USD cost based on token counts and model pricing."""
    for known_model, (p_price, c_price) in PRICING_TABLE.items():
        if known_model in model_name.lower():
            cost = (prompt_tokens * p_price / 1_000_000.0) + (
                completion_tokens * c_price / 1_000_000.0
            )
            return round(cost, 6)
    return 0.0


class LLMProvider(ABC):
    """Base interface for swappable LLM adapters."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Execute a text completion or function-calling request."""
        pass
