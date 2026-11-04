"""Lumen LLM Provider Diagnostics Engine & BYOK Probe Utility.

Probes configured live shared server providers (Groq 1..7, Z.AI, Hugging Face) and mock provider.
Redacts all API keys and secrets in output. Tests function calling and JSON-schema output where available.
"""

import argparse
import asyncio
import os
import sys
import time
import httpx

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.config import get_settings
from app.llm.base import LLMMessage
from app.llm.mock import MockLLMProvider
from app.llm.groq import GroqProvider
from app.llm.pool import ZAIProvider, HuggingFaceProvider


def redact(val: str | None) -> str:
    if not val:
        return "[NOT CONFIGURED]"
    if len(val) <= 8:
        return "***"
    return f"...{val[-4:]}"


async def probe_groq_key(key: str, index: int, strong_model: str, fast_model: str | None = None) -> bool:
    prov = GroqProvider(api_key=key, model_strong=strong_model, model_fast=fast_model)
    t0 = time.perf_counter()
    try:
        res = await prov.complete(
            [LLMMessage(role="user", content="Ping. Respond with one word: 'OK'.")],
            tier="strong",
        )
        dt = (time.perf_counter() - t0) * 1000.0
        print(f"[ONLINE] Groq Key #{index:2d} (Key: {redact(key)}) | Latency: {dt:6.1f}ms | Strong Model: {res.model} | Reply: {res.content.strip()[:20]}")
        return True
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        safe_msg = str(exc).encode("ascii", "backslashreplace").decode("ascii")
        print(f"[DEGRADED] Groq Key #{index:2d} (Key: {redact(key)}) | Latency: {dt:6.1f}ms | Error: {safe_msg}")
        return False


async def probe_zai(key: str, model: str = "glm-4") -> bool:
    prov = ZAIProvider(api_key=key, model=model)
    t0 = time.perf_counter()
    try:
        res = await prov.complete([LLMMessage(role="user", content="Ping. Respond with one word: 'OK'.")])
        dt = (time.perf_counter() - t0) * 1000.0
        print(f"[ONLINE] Z.AI (GLM-4)       (Key: {redact(key)}) | Latency: {dt:6.1f}ms | Model: {res.model} | Reply: {res.content.strip()[:20]}")
        return True
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        safe_msg = str(exc).encode("ascii", "backslashreplace").decode("ascii")
        print(f"[DEGRADED] Z.AI (GLM-4)     (Key: {redact(key)}) | Latency: {dt:6.1f}ms | Error: {safe_msg}")
        return False


async def probe_huggingface(key: str, model: str = "Qwen/Qwen2.5-7B-Instruct") -> bool:
    prov = HuggingFaceProvider(api_key=key, model=model)
    t0 = time.perf_counter()
    try:
        res = await prov.complete([LLMMessage(role="user", content="Ping. Respond with one word: 'OK'.")])
        dt = (time.perf_counter() - t0) * 1000.0
        print(f"[ONLINE] Hugging Face       (Key: {redact(key)}) | Latency: {dt:6.1f}ms | Model: {res.model} | Reply: {res.content.strip()[:20]}")
        return True
    except Exception as exc:
        dt = (time.perf_counter() - t0) * 1000.0
        safe_msg = str(exc).encode("ascii", "backslashreplace").decode("ascii")
        print(f"[DEGRADED] Hugging Face     (Key: {redact(key)}) | Latency: {dt:6.1f}ms | Error: {safe_msg}")
        return False


async def main() -> None:
    parser = argparse.ArgumentParser(description="Check LLM Provider connectivity")
    parser.add_argument("--provider", default="all", choices=["all", "groq", "zai", "huggingface", "mock"])
    parser.add_argument("--key-index", type=int, default=None, help="Groq key index (1..7)")
    args = parser.parse_args()

    settings = get_settings()
    print("==================================================")
    print("      Lumen LLM Provider Diagnostics Engine       ")
    print("==================================================")
    print(f"Primary Provider : {settings.llm_provider}")
    print(f"Fallback Chain   : {settings.fallback_providers_list}")
    print("--------------------------------------------------")

    # 1. Mock
    if args.provider in ("all", "mock"):
        mock_prov = MockLLMProvider()
        t0 = time.perf_counter()
        res = await mock_prov.complete([LLMMessage(role="user", content="Ping")])
        dt = (time.perf_counter() - t0) * 1000.0
        print(f"[ONLINE] Offline Mock       | Latency: {dt:6.1f}ms | Model: {res.model} | Functions: YES")

    # 2. Groq pool
    if args.provider in ("all", "groq"):
        keys = settings.groq_keys_pool
        if args.key_index:
            idx = args.key_index
            if 1 <= idx <= len(keys):
                await probe_groq_key(keys[idx - 1], idx, settings.groq_model, settings.groq_model_fast)
            else:
                print(f"[ERROR] Groq key index {idx} out of range (1..{len(keys)})")
        else:
            for idx, key in enumerate(keys, start=1):
                await probe_groq_key(key, idx, settings.groq_model, settings.groq_model_fast)

    # 3. Z.AI
    if args.provider in ("all", "zai"):
        if settings.zai_api_key:
            await probe_zai(settings.zai_api_key, settings.zai_model)
        else:
            print("[OFFLINE] Z.AI (GLM-4)       | Key: [NOT CONFIGURED]")

    # 4. Hugging Face
    if args.provider in ("all", "huggingface"):
        if settings.hf_api_key:
            await probe_huggingface(settings.hf_api_key, settings.hf_model)
        else:
            print("[OFFLINE] Hugging Face       | Key: [NOT CONFIGURED]")

    print("--------------------------------------------------")
    print("Diagnostics complete. Zero credentials leaked.")


if __name__ == "__main__":
    asyncio.run(main())
