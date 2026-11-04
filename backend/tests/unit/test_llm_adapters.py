"""Unit tests for swappable LLM adapters using respx HTTP fixtures."""

import httpx
import pytest
import respx

from app.llm.base import (
    LLMMessage,
    LLMRateLimitError,
    ToolDefinition,
    calculate_cost_usd,
)
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.openrouter import OpenRouterProvider


@pytest.mark.asyncio
async def test_mock_provider_deterministic_intents() -> None:
    provider = MockLLMProvider()

    # 1. Router classification
    resp_route = await provider.complete(
        [LLMMessage(role="user", content="Which product has highest revenue?")],
        json_schema={"type": "object", "properties": {"lane": {"type": "string"}}},
    )
    assert "analysis" in resp_route.content

    # 2. Plan generation
    resp_plan = await provider.complete(
        [LLMMessage(role="user", content="Plan execution for sales")],
        json_schema={"type": "object", "properties": {"dag": {"type": "object"}}},
    )
    assert "sql_tool" in resp_plan.content

    # 3. Known truth Q&A
    resp_rev = await provider.complete(
        [LLMMessage(role="user", content="Show top region with highest revenue")]
    )
    assert "$1,482,900.00" in resp_rev.content

    # 4. Cost calculation
    assert calculate_cost_usd("mock", 1000, 500) == 0.0


@pytest.mark.asyncio
@respx.mock
async def test_gemini_provider_success() -> None:
    provider = GeminiProvider(api_key="test-gemini-key")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=test-gemini-key"

    mock_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Analysis complete."},
                        {"functionCall": {"name": "sql_tool", "args": {"sql": "SELECT 1;"}}},
                    ]
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 150,
            "candidatesTokenCount": 40,
        },
    }

    respx.post(url).mock(return_value=httpx.Response(200, json=mock_payload))

    resp = await provider.complete(
        [LLMMessage(role="user", content="Run SQL")],
        tools=[ToolDefinition(name="sql_tool", description="exec", parameters={})],
        tier="fast",
    )
    assert resp.content == "Analysis complete."
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].function_name == "sql_tool"
    assert resp.prompt_tokens == 150
    assert resp.completion_tokens == 40
    assert resp.cost_usd > 0.0
    assert resp.provider == "gemini"


@pytest.mark.asyncio
@respx.mock
async def test_gemini_provider_rate_limit() -> None:
    provider = GeminiProvider(api_key="test-key")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=test-key"
    respx.post(url).mock(return_value=httpx.Response(429, json={"error": "RESOURCE_EXHAUSTED"}))

    with pytest.raises(LLMRateLimitError):
        await provider.complete([LLMMessage(role="user", content="Hi")])


@pytest.mark.asyncio
@respx.mock
async def test_groq_provider_success() -> None:
    provider = GroqProvider(api_key="gsk-test")
    url = "https://api.groq.com/openai/v1/chat/completions"

    mock_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Groq inference output.",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "chart_tool", "arguments": '{"type": "bar"}'},
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 80, "completion_tokens": 20},
    }

    respx.post(url).mock(return_value=httpx.Response(200, json=mock_payload))

    resp = await provider.complete(
        [LLMMessage(role="user", content="Draw bar chart")],
        tier="fast",
    )
    assert resp.content == "Groq inference output."
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].function_name == "chart_tool"
    assert resp.tool_calls[0].arguments == {"type": "bar"}
    assert resp.provider == "groq"


@pytest.mark.asyncio
@respx.mock
async def test_openrouter_provider_success() -> None:
    provider = OpenRouterProvider(api_key="sk-or-test")
    url = "https://openrouter.ai/api/v1/chat/completions"

    mock_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "OpenRouter output response.",
                }
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30},
    }

    respx.post(url).mock(return_value=httpx.Response(200, json=mock_payload))

    resp = await provider.complete([LLMMessage(role="user", content="Analyze data")])
    assert resp.content == "OpenRouter output response."
    assert resp.provider == "openrouter"


@pytest.mark.asyncio
@respx.mock
async def test_openai_compat_provider_success() -> None:
    provider = OpenAICompatProvider(base_url="https://api.custom-ai.com/v1", api_key="sk-custom")
    url = "https://api.custom-ai.com/v1/chat/completions"

    mock_payload = {
        "choices": [{"message": {"role": "assistant", "content": "Custom model response."}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 25},
    }

    respx.post(url).mock(return_value=httpx.Response(200, json=mock_payload))

    resp = await provider.complete([LLMMessage(role="user", content="Hello")])
    assert resp.content == "Custom model response."
    assert resp.provider == "openai_compat"
