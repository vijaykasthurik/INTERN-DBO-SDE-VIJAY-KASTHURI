"""OpenRouter unified REST LLM adapter."""

import json
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

import httpx

from app.config import get_settings
from app.llm.base import (
    LLMAuthenticationError,
    LLMMessage,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    LLMServerError,
    LLMTimeoutError,
    ToolCall,
    ToolDefinition,
    calculate_cost_usd,
)


class OpenRouterProvider(LLMProvider):
    """OpenRouter API adapter providing multi-model routing via OpenAI-compatible endpoints."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openrouter_api_key
        self.fast_model = settings.openrouter_model_fast or "google/gemini-2.0-flash-001"
        self.strong_model = settings.openrouter_model_strong or "anthropic/claude-3.5-sonnet"
        self.client = httpx.AsyncClient(timeout=30.0)

    def _select_model(self, tier: Literal["fast", "strong"]) -> str:
        return self.strong_model if tier == "strong" else self.fast_model

    def _build_payload(
        self,
        messages: list[LLMMessage],
        model: str,
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        formatted_msgs = []
        for msg in messages:
            formatted_msg: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                formatted_msg["name"] = msg.name
            if msg.tool_call_id:
                formatted_msg["tool_call_id"] = msg.tool_call_id
            formatted_msgs.append(formatted_msg)

        payload: dict[str, Any] = {
            "model": model,
            "messages": formatted_msgs,
            "stream": stream,
        }

        if json_schema:
            payload["response_format"] = {"type": "json_object"}

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        return payload

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Execute request via OpenRouter."""
        model = self._select_model(tier)
        payload = self._build_payload(
            messages, model, tools=tools, json_schema=json_schema, stream=stream
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://lumen.local",
            "X-Title": "Lumen AI",
            "Content-Type": "application/json",
        }
        start_time = time.perf_counter()

        if stream:
            return self._stream_response(payload, headers)

        try:
            resp = await self.client.post(self.BASE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise LLMRateLimitError(
                    f"OpenRouter rate limit (429): {e}", provider="openrouter", status_code=status
                ) from e
            elif status in (401, 403):
                raise LLMAuthenticationError(
                    f"OpenRouter auth error ({status}): {e}",
                    provider="openrouter",
                    status_code=status,
                ) from e
            elif status >= 500:
                raise LLMServerError(
                    f"OpenRouter server error ({status}): {e}",
                    provider="openrouter",
                    status_code=status,
                ) from e
            raise LLMProviderError(
                f"OpenRouter HTTP error ({status}): {e}", provider="openrouter", status_code=status
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"OpenRouter request timed out: {e}", provider="openrouter"
            ) from e
        except httpx.RequestError as e:
            raise LLMProviderError(f"OpenRouter network error: {e}", provider="openrouter") from e

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""

        tool_calls: list[ToolCall] = []
        raw_tool_calls = msg.get("tool_calls", [])
        for tc in raw_tool_calls:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", "call_openrouter"),
                    function_name=fn.get("name", ""),
                    arguments=args,
                )
            )

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        cost_usd = calculate_cost_usd(model, prompt_tokens, completion_tokens)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=round(latency_ms, 2),
            provider="openrouter",
            model=model,
        )

    async def _stream_response(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> AsyncGenerator[str, None]:
        """Stream SSE deltas from OpenRouter."""
        try:
            async with self.client.stream(
                "POST", self.BASE_URL, json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if raw and raw != "[DONE]":
                            chunk = json.loads(raw)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise LLMRateLimitError(
                    f"OpenRouter stream rate limit: {e}", provider="openrouter", status_code=status
                ) from e
            raise LLMProviderError(
                f"OpenRouter stream error: {e}", provider="openrouter", status_code=status
            ) from e
