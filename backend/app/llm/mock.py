"""Deterministic, rule-based Mock LLM provider for offline demo and verification."""

import json
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

from app.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    ToolCall,
    ToolDefinition,
)


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

        # Default response
        content = "Analysis completed based on validated Evidence Ledger entries."
        tool_calls: list[ToolCall] = []

        # 1. Routing classification if requested
        if json_schema and "lane" in json.dumps(json_schema):
            if "sql" in last_prompt or "code" in last_prompt:
                content = json.dumps(
                    {"lane": "code_request", "confidence": 0.98, "reason": "Code request"}
                )
            elif "anomaly" in last_prompt or "outlier" in last_prompt:
                content = json.dumps(
                    {"lane": "anomaly", "confidence": 0.95, "reason": "Anomaly detection"}
                )
            elif "forecast" in last_prompt or "future" in last_prompt:
                content = json.dumps(
                    {"lane": "forecast", "confidence": 0.92, "reason": "Forecasting query"}
                )
            elif "why" in last_prompt:
                content = json.dumps(
                    {"lane": "investigation", "confidence": 0.94, "reason": "Root cause analysis"}
                )
            elif "dashboard" in last_prompt:
                content = json.dumps(
                    {"lane": "dashboard", "confidence": 0.96, "reason": "Dashboard request"}
                )
            else:
                content = json.dumps(
                    {"lane": "analysis", "confidence": 0.90, "reason": "Analytical aggregation"}
                )

        # 2. Plan generation if requested
        elif json_schema and "dag" in json.dumps(json_schema):
            content = json.dumps(
                {
                    "dag": {
                        "steps": [
                            {
                                "id": "step_1",
                                "tool": "sql_tool",
                                "description": "Execute DuckDB aggregation over sales table",
                                "parameters": {
                                    "sql": "SELECT region, SUM(quantity * unit_price * (1 - discount)) AS revenue FROM sales GROUP BY region ORDER BY revenue DESC LIMIT 1;"
                                },
                            }
                        ]
                    }
                }
            )

        # 3. Questions answering
        elif "highest revenue" in last_prompt or "top region" in last_prompt:
            content = (
                "North America generated the highest total revenue at $1,482,900.00 across 1,820 orders. "
                "This was driven by strong enterprise software adoption."
            )
        elif "monthly sales" in last_prompt or "trend" in last_prompt:
            content = (
                "Monthly sales trend demonstrates consistent revenue growth with seasonal peaks in Q4. "
                "In March 2024, EMEA experienced a notable 34.2% dip before recovering."
            )
        elif "underperforming" in last_prompt or "lowest" in last_prompt:
            content = (
                "The lowest revenue products are PROD-014 ($12,400.00), PROD-031 ($15,100.00), "
                "and PROD-048 ($16,800.00) due to low order volume."
            )
        elif "top five customers" in last_prompt or "top customers" in last_prompt:
            content = (
                "The top five customers by spend are CUST-0042 ($284,500.00), CUST-0115 ($261,200.00), "
                "CUST-0210 ($245,800.00), CUST-0340 ($238,900.00), and CUST-0512 ($229,400.00)."
            )
        elif "anomaly" in last_prompt or "outlier" in last_prompt:
            content = (
                "Detected 5 giant outlier orders with unit prices exceeding 3 standard deviations: "
                "ORD-OUT-01 through ORD-OUT-05, and 1 duplicate block of 3 orders."
            )
        elif "why" in last_prompt and ("dip" in last_prompt or "drop" in last_prompt):
            content = (
                "The EMEA revenue drop in March 2024 was caused by a regional hardware supply disruption "
                "which decreased order fulfillment by 65% in that territory."
            )
        elif "generate sql" in last_prompt or "show sql" in last_prompt:
            content = (
                "```sql\n"
                "SELECT region, SUM(quantity * unit_price * (1 - discount)) AS total_revenue\n"
                "FROM sales\n"
                "GROUP BY region\n"
                "ORDER BY total_revenue DESC;\n"
                "```\n"
                "This query aggregates net revenue by region after deducting discounts."
            )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if stream:

            async def _streamer() -> AsyncGenerator[str, None]:
                words = content.split(" ")
                for word in words:
                    yield f"{word} "

            return _streamer()

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            prompt_tokens=32,
            completion_tokens=len(content.split()),
            cost_usd=0.0,
            latency_ms=latency_ms,
            provider="mock",
            model="mock-deterministic-v1",
        )
