"""Provider diagnostic utility: validates connectivity and latency across configured LLM providers."""

import asyncio
import time
from app.config import get_settings
from app.llm.mock import MockLLMProvider
from app.llm.base import LLMMessage


async def check_all_providers() -> None:
    settings = get_settings()
    print("=== Lumen LLM Connectivity Diagnostics ===")
    print(f"Primary Provider: {settings.llm_provider}")
    print(f"Fallback Order: {settings.fallback_providers_list}")

    mock_prov = MockLLMProvider()
    t0 = time.perf_counter()
    res = await mock_prov.complete([LLMMessage(role="user", content="Ping")])
    dt = (time.perf_counter() - t0) * 1000.0

    print(f"[OK] Provider 'mock' is available. Latency: {dt:.2f}ms. Model: {res.model}")


if __name__ == "__main__":
    asyncio.run(check_all_providers())
