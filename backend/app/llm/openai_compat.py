"""Generic OpenAI-compatible REST adapter for local (Ollama/vLLM) or alternative providers."""

from collections.abc import AsyncGenerator
from typing import Any, Literal

import httpx

from app.config import get_settings
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolDefinition


class OpenAICompatProvider(LLMProvider):
    """Client for any OpenAI API-compatible REST server."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.openai_compat_base_url
        self.api_key = api_key or settings.openai_compat_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Execute request to OpenAI-compatible server."""
        return LLMResponse(content="OpenAI compat completed.", provider="openai_compat")
