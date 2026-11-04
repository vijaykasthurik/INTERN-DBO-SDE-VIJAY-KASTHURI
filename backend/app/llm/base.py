"""Abstract base classes and response models for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Literal

from pydantic import BaseModel, Field


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
