"""Deterministic, rule-based Mock LLM provider for offline demo and verification."""

import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolDefinition


class MockLLMProvider(LLMProvider):
    """Deterministic offline provider implementing router classification, planning, and SQL generation."""

    def __init__(self) -> None:
        self.provider_name = "mock"

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        json_schema: dict[str, Any] | None = None,
        tier: Literal["fast", "strong"] = "fast",
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Return deterministic responses mapped to standard intents."""
        start_time = time.perf_counter()
        last_prompt = messages[-1].content.lower() if messages else ""

        content = "Analysis completed based on validated Evidence Ledger entries."

        if "highest revenue" in last_prompt or "top region" in last_prompt:
            content = "North America generated the highest total revenue at $1,482,900.00 across 1,820 orders."
        elif "monthly sales" in last_prompt or "trend" in last_prompt:
            content = "Monthly sales demonstrate strong seasonal peaks in Q4, with EMEA experiencing a 34.2% dip in March."
        elif "anomaly" in last_prompt or "outlier" in last_prompt:
            content = "Detected 5 giant outlier transactions with unit prices exceeding 3 standard deviations."
        elif "sql" in last_prompt:
            content = "SELECT region, SUM(quantity * unit_price * (1 - discount)) AS total_revenue FROM sales GROUP BY region ORDER BY total_revenue DESC;"

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if stream:
            async def _streamer() -> AsyncGenerator[str, None]:
                words = content.split(" ")
                for word in words:
                    yield f"{word} "

            return _streamer()

        return LLMResponse(
            content=content,
            prompt_tokens=42,
            completion_tokens=len(content.split()),
            cost_usd=0.0,
            latency_ms=latency_ms,
            provider="mock",
            model="mock-deterministic-v1",
        )
