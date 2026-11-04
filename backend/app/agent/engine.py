"""PEVN Agent Engine: Orchestrates Plan-Execute-Verify-Narrate lifecycle with streaming SSE."""

import asyncio
import os
import pathlib
import time
from collections.abc import AsyncGenerator
from typing import Any

import duckdb

from app.agent.context import ContextResolver
from app.agent.events import AgentEvent
from app.agent.executor import StepExecutor
from app.agent.ledger import EvidenceLedger
from app.agent.memory import AgentMemory
from app.agent.narrator import Narrator
from app.agent.planner import ExecutionPlanner
from app.agent.router import IntentRouter
from app.agent.verifier import Verifier
from app.data.ingestion import DataIngestionPipeline
from app.tools.chart_tool import ChartTool
from app.tools.pandas_tool import PandasTool
from app.tools.search_tool import SearchTool
from app.tools.sql_tool import SQLTool


def ensure_user_warehouse(user_id: int) -> tuple[str, list[str]]:
    """Ensure per-user DuckDB warehouse exists, seeded with sample tables if not populated."""
    pipeline = DataIngestionPipeline()
    db_path = pipeline.get_user_db_path(user_id)

    con = duckdb.connect(db_path)
    try:
        tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        if not tables:
            # Seed with sample data tables if available
            sample_dir = pathlib.Path(__file__).resolve().parents[3] / "sample_data"
            for f_name in ["sales.csv", "customers.csv", "products.csv"]:
                p = sample_dir / f_name
                if p.exists():
                    table_name = os.path.splitext(f_name)[0]
                    con.execute(
                        f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{p.as_posix()}')"
                    )
            tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    finally:
        con.close()

    return db_path, tables


class AgentEngine:
    """Core autonomous analyst executing PEVN pipeline with verifiable Evidence Ledger."""

    def __init__(self) -> None:
        self.context_resolver = ContextResolver()
        self.router = IntentRouter()
        self.planner = ExecutionPlanner()
        self.verifier = Verifier()
        self.narrator = Narrator()

    async def run(
        self,
        question: str,
        session_id: str,
        user_id: int,
        trace_id: str,
        memory: AgentMemory | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute question pipeline emitting live SSE events."""
        start_time = time.perf_counter()

        # Step 1: Context and Entity Resolution
        resolved_question, extracted_entities = self.context_resolver.resolve(question, memory)

        # Step 2: Intent Routing
        route = self.router.route(resolved_question)
        yield AgentEvent(
            event_type="route",
            trace_id=trace_id,
            payload={
                "lane": route.lane,
                "confidence": route.confidence,
                "reason": route.reason,
                "resolved_question": resolved_question,
            },
        )

        # Handle Clarify Lane (ambiguous input -> ask 1 precise question with tappable options)
        if route.lane == "clarify":
            yield AgentEvent(
                event_type="final",
                trace_id=trace_id,
                payload={
                    "direct_answer": route.clarification_question or "Please clarify your request.",
                    "business_insight": "Clarification required to narrow analytical focus.",
                    "how_i_got_this": "Input ambiguous, prompting user options.",
                    "confidence": "High",
                    "clarification_options": route.clarification_options,
                    "suggested_followups": route.clarification_options[:3],
                },
            )
            yield AgentEvent(
                event_type="done", trace_id=trace_id, payload={"status": "clarification_needed"}
            )
            return

        # Step 3: Execution Planning (DAG)
        dag = self.planner.plan(resolved_question, route.lane)
        yield AgentEvent(
            event_type="plan",
            trace_id=trace_id,
            payload={"dag": dag.model_dump()},
        )

        # Prepare Per-Tenant Isolated Tools
        db_path, allowed_tables = ensure_user_warehouse(user_id)
        tools_registry: dict[str, Any] = {
            "sql_tool": SQLTool(db_path=db_path, allowed_tables=allowed_tables),
            "pandas_tool": PandasTool(),
            "chart_tool": ChartTool(),
            "search_tool": SearchTool(),
        }

        # Step 4: Concurrent DAG Step Execution with Evidence Ledger
        executor = StepExecutor(tools_registry=tools_registry)
        ledger = EvidenceLedger()

        # Queue for capturing streaming step events from the executor
        event_queue: asyncio.Queue[AgentEvent] = asyncio.Queue()

        async def _step_event_callback(event_type: str, payload: dict[str, Any]) -> None:
            await event_queue.put(
                AgentEvent(
                    event_type=event_type,  # type: ignore
                    trace_id=trace_id,
                    payload=payload,
                )
            )

        # Run DAG in background task while draining event queue
        exec_task = asyncio.create_task(
            executor.execute_dag(dag, ledger, step_event_callback=_step_event_callback)
        )

        while not exec_task.done() or not event_queue.empty():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.05)
                yield event
            except TimeoutError:
                continue

        await exec_task  # Ensure any exceptions propagate

        # Step 5: Verification (Skeptic)
        verification = self.verifier.verify(
            draft_answer="Computed analytical aggregation metrics.",
            ledger=ledger,
        )
        yield AgentEvent(
            event_type="verify",
            trace_id=trace_id,
            payload=verification.model_dump(),
        )

        # Step 6: Narration & Token Streaming
        narrative = self.narrator.compose_final(
            question=resolved_question,
            lane=route.lane,
            ledger=ledger,
            confidence=verification.confidence,
        )

        # Yield Chart event if chart was produced
        if narrative.chart_spec:
            yield AgentEvent(
                event_type="chart",
                trace_id=trace_id,
                payload={"chart_spec": narrative.chart_spec},
            )

        # Stream narrative tokens
        async for token in self.narrator.stream_tokens(narrative.direct_answer):
            yield AgentEvent(
                event_type="token",
                trace_id=trace_id,
                payload={"delta": token},
            )

        # Yield Final Complete Narrative
        yield AgentEvent(
            event_type="final",
            trace_id=trace_id,
            payload=narrative.model_dump(),
        )

        # Step 7: Completion event
        total_time_ms = (time.perf_counter() - start_time) * 1000.0
        yield AgentEvent(
            event_type="done",
            trace_id=trace_id,
            payload={"status": "success", "runtime_ms": round(total_time_ms, 2)},
        )

        # Update Session Memory if provided
        if memory:
            memory.record_turn(
                user_question=question,
                resolved_question=resolved_question,
                lane=route.lane,
                final_answer=narrative.direct_answer,
                entities=extracted_entities,
                sql_query=narrative.sql_code,
            )
