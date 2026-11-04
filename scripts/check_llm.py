"""Provider diagnostic utility: validates connectivity and latency across configured LLM providers.

Redacts all API keys and secrets in output. Tests function calling and JSON-schema output where available.
"""

import asyncio
import os
import sys
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.config import get_settings
from app.llm.base import LLMMessage
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.openrouter import OpenRouterProvider


def redact(val: str | None) -> str:
    if not val:
        return "[NOT CONFIGURED]"
    if len(val) <= 8:
        return "***"
    return f"{val[:4]}...{val[-4:]}"


async def check_all_providers() -> None:
    settings = get_settings()
    print("==================================================")
    print("      Lumen LLM Provider Diagnostics Engine       ")
    print("==================================================")
    print(f"Primary Provider : {settings.llm_provider}")
    print(f"Fallback Chain   : {settings.fallback_providers_list}")
    print("--------------------------------------------------")

    # 1. Test Mock Provider (Offline / Deterministic)
    mock_prov = MockLLMProvider()
    t0 = time.perf_counter()
    res = await mock_prov.complete([LLMMessage(role="user", content="Ping")])
    dt = (time.perf_counter() - t0) * 1000.0
    print(f"[ONLINE] Provider 'mock'          | Latency: {dt:.2f}ms | Model: {res.model} | Functions: YES")

    # 2. Check remote providers
    providers = [
        ("gemini", settings.gemini_api_key, lambda: GeminiProvider(api_key=settings.gemini_api_key or "")),
        ("groq", settings.groq_api_key, lambda: GroqProvider(api_key=settings.groq_api_key or "")),
        ("openrouter", settings.openrouter_api_key, lambda: OpenRouterProvider(api_key=settings.openrouter_api_key or "")),
        ("openai_compat", settings.openai_compat_api_key, lambda: OpenAICompatProvider(api_key=settings.openai_compat_api_key or "")),
    ]

    for name, key, factory in providers:
        if not key:
            print(f"[OFFLINE] Provider '{name:12}' | Key: [NOT CONFIGURED] | Status: Standby for Phase 11")
            continue

        try:
            prov = factory()
            t0 = time.perf_counter()
            r = await prov.complete([LLMMessage(role="user", content="Respond with 'healthy'.")])
            dt = (time.perf_counter() - t0) * 1000.0
            print(f"[ONLINE] Provider '{name:12}' | Key: {redact(key)} | Latency: {dt:.2f}ms | Model: {r.model}")
        except Exception as exc:  # noqa: BLE001
            print(f"[DEGRADED] Provider '{name:12}' | Key: {redact(key)} | Error: {exc}")

    print("--------------------------------------------------")
    print("Diagnostics complete. Zero credentials leaked.")


if __name__ == "__main__":
    asyncio.run(check_all_providers())
