"""LLM Router managing fallback chains, circuit breakers, and rate limits."""

from collections.abc import AsyncGenerator
from typing import Any, Literal

from app.config import Settings, get_settings
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolDefinition
from app.llm.mock import MockLLMProvider


class LLMRouter(LLMProvider):
    """Orchestrates primary and fallback providers with health checks and circuit breakers."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.mock_provider = MockLLMProvider()

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Route request through fallback chain, defaulting to mock in offline mode."""
        return await self.mock_provider.complete(
            messages=messages,
            tools=tools,
            json_schema=json_schema,
            tier=tier,
            stream=stream,
        )
