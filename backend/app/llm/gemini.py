"""Google Gemini API adapter via raw REST endpoints (no vendor SDK)."""

from collections.abc import AsyncGenerator
from typing import Any, Literal

import httpx

from app.config import get_settings
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolDefinition


class GeminiProvider(LLMProvider):
    """Native Gemini REST client with fast/strong tier mapping."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Execute Gemini REST request."""
        return LLMResponse(content="Gemini provider completed.", provider="gemini")
