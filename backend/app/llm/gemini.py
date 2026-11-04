"""Google Gemini API adapter via raw REST endpoints (no vendor SDK)."""

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


class GeminiProvider(LLMProvider):
    """Native Gemini REST client with fast/strong tier mapping."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.fast_model = settings.gemini_model_fast or "gemini-2.0-flash"
        self.strong_model = settings.gemini_model_strong or "gemini-2.0-flash-thinking-exp-01-21"
        self.client = httpx.AsyncClient(timeout=30.0)

    def _select_model(self, tier: Literal["fast", "strong"]) -> str:
        return self.strong_model if tier == "strong" else self.fast_model

    def _build_payload(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert standard messages and tools into Gemini REST schema."""
        contents: list[dict[str, Any]] = []
        system_instruction_parts: list[dict[str, str]] = []

        for msg in messages:
            if msg.role == "system":
                system_instruction_parts.append({"text": msg.content})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})
            elif msg.role == "tool":
                contents.append(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": msg.name or "tool_result",
                                    "response": {"output": msg.content},
                                }
                            }
                        ],
                    }
                )
            else:  # user
                contents.append({"role": "user", "parts": [{"text": msg.content}]})

        payload: dict[str, Any] = {"contents": contents}

        if system_instruction_parts:
            payload["systemInstruction"] = {"parts": system_instruction_parts}

        generation_config: dict[str, Any] = {}
        if json_schema:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = json_schema
        if generation_config:
            payload["generationConfig"] = generation_config

        if tools:
            declarations = [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
                for t in tools
            ]
            payload["tools"] = [{"functionDeclarations": declarations}]

        return payload

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Execute Gemini REST request."""
        model = self._select_model(tier)
        payload = self._build_payload(messages=messages, tools=tools, json_schema=json_schema)
        start_time = time.perf_counter()

        if stream:
            url = f"{self.BASE_URL}/{model}:streamGenerateContent?alt=sse&key={self.api_key}"
            return self._stream_response(url, payload)

        url = f"{self.BASE_URL}/{model}:generateContent?key={self.api_key}"
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise LLMRateLimitError(
                    f"Gemini rate limit exceeded (429): {e}", provider="gemini", status_code=status
                ) from e
            elif status in (401, 403):
                raise LLMAuthenticationError(
                    f"Gemini authentication failed ({status}): {e}",
                    provider="gemini",
                    status_code=status,
                ) from e
            elif status >= 500:
                raise LLMServerError(
                    f"Gemini server error ({status}): {e}", provider="gemini", status_code=status
                ) from e
            raise LLMProviderError(
                f"Gemini HTTP error ({status}): {e}", provider="gemini", status_code=status
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Gemini request timed out: {e}", provider="gemini") from e
        except httpx.RequestError as e:
            raise LLMProviderError(f"Gemini network error: {e}", provider="gemini") from e

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Parse content and tool calls
        content_text = ""
        tool_calls: list[ToolCall] = []

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for i, part in enumerate(parts):
                if "text" in part:
                    content_text += part["text"]
                if "functionCall" in part:
                    fc = part["functionCall"]
                    tool_calls.append(
                        ToolCall(
                            id=f"gemini_call_{i}",
                            function_name=fc.get("name", ""),
                            arguments=fc.get("args", {}),
                        )
                    )

        # Token accounting
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        cost_usd = calculate_cost_usd(model, prompt_tokens, completion_tokens)

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=round(latency_ms, 2),
            provider="gemini",
            model=model,
        )

    async def _stream_response(
        self, url: str, payload: dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Stream SSE deltas from Gemini."""
        try:
            async with self.client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        raw_json = line[6:].strip()
                        if raw_json and raw_json != "[DONE]":
                            chunk = json.loads(raw_json)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        yield part["text"]
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise LLMRateLimitError(
                    f"Gemini streaming rate limit: {e}", provider="gemini", status_code=status
                ) from e
            raise LLMProviderError(
                f"Gemini stream HTTP error: {e}", provider="gemini", status_code=status
            ) from e
