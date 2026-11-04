"""PEVN Agent Engine: Orchestrates Plan-Execute-Verify-Narrate lifecycle with streaming SSE."""

import asyncio
import hashlib
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import duckdb
import structlog

from app.agent.cache import VerifiedAnswerCache
from app.agent.context import ContextResolver
from app.agent.events import AgentEvent
from app.agent.executor import StepExecutor
from app.agent.ledger import EvidenceLedger
from app.agent.memory import AgentMemory
from app.agent.narrator import FinalNarrative, Narrator
from app.agent.planner import ExecutionPlanner, PlanDAG, PlanStep
from app.agent.router import IntentRouter
from app.agent.verifier import Verifier
from app.config import get_settings
from app.data.ingestion import DataIngestionPipeline
from app.llm.base import LLMMessage, LLMResponse
from app.llm.budget import BudgetGovernor
from app.llm.router import LLMRouter
from app.tools.anomaly_tool import AnomalyTool
from app.tools.chart_tool import ChartTool
from app.tools.forecast_tool import ForecastTool
from app.tools.hypothesis_tool import HypothesisTool
from app.tools.pandas_tool import PandasTool
from app.tools.search_tool import SearchTool
from app.tools.sql_tool import SQLTool

logger = structlog.get_logger(__name__)


def ensure_user_warehouse(user_id: int) -> tuple[str, list[str]]:
    """Return only tables explicitly uploaded by this tenant; never seed hidden sample data."""
    pipeline = DataIngestionPipeline()
    db_path = pipeline.get_user_db_path(user_id)

    con = duckdb.connect(db_path)
    try:
        tables = [str(row[0]) for row in con.execute("SHOW TABLES").fetchall()]
    finally:
        con.close()

    return db_path, tables


def _get_table_schema_summary(db_path: str, tables: list[str]) -> str:
    """Extract table and column definitions from user DuckDB warehouse for LLM context."""
    lines: list[str] = []
    con = duckdb.connect(db_path, read_only=True)
    try:
        for t in tables:
            try:
                cols = con.execute(f"PRAGMA table_info('{t}')").fetchall()
                col_defs = [f"{c[1]} ({c[2]})" for c in cols]
                lines.append(f"- Table '{t}': {', '.join(col_defs)}")
            except Exception:
                lines.append(f"- Table '{t}'")
    finally:
        con.close()
    return "\n".join(lines)


class AgentEngine:
    """Core autonomous analyst executing PEVN pipeline with verifiable Evidence Ledger."""

    def __init__(self) -> None:
        self.context_resolver = ContextResolver()
        self.router = IntentRouter()
        self.planner = ExecutionPlanner()
        self.verifier = Verifier()
        self.narrator = Narrator()
        self.cache = VerifiedAnswerCache()
        self.llm_router = LLMRouter()

    async def plan_with_llm(
        self,
        question: str,
        lane: str,
        allowed_tables: list[str],
        db_path: str,
        user_id: int,
        user_key: Any = None,
        allow_shared_fallback: bool = True,
    ) -> PlanDAG | None:
        """Dynamically generate execution plan and SQL query using active live LLM provider."""
        schema_summary = _get_table_schema_summary(db_path, allowed_tables)
        prompt = f"""You are Lumen's Autonomous SQL & Analytics Planner.
Database Schema:
{schema_summary}

User Question: "{question}"
Analytical Intent Lane: "{lane}"

Rules:
1. If the question asks for statistical anomaly or outlier detection, set "tool": "anomaly_tool".
2. If the question asks for time-series forecasting or projections into the future, set "tool": "forecast_tool".
3. If the question investigates why a metric dropped or changed, set "tool": "hypothesis_tool".
4. For all other data queries, calculations, aggregations, and trends, set "tool": "sql_tool":
   - The query MUST be a SELECT-only DuckDB SQL query. No mutations.
   - Standard net revenue definition: SUM(quantity * unit_price * (1 - discount))
   - For string aggregation: use string_agg(column, ', ') or list(column). Do not use list_agg.
   - For monthly trends: use STRFTIME(CAST(order_date AS DATE), '%Y-%m') AS month.
   - For YoY growth: use a CTE and window function LAG(revenue, 12) OVER (ORDER BY month). Avoid INTERVAL arithmetic.
   - Recommended chart type: 'bar' (rankings/comparisons), 'line' (time series), 'pie' (shares), 'scatter', or 'none'.

Respond ONLY with valid JSON conforming to:
{{
  "tool": "sql_tool",
  "sql": "SELECT ...",
  "chart_type": "bar",
  "description": "Short explanation of the step"
}}"""

        res = await self.llm_router.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            tier="strong",
            user_id=user_id,
            user_key=user_key,
            allow_shared_fallback=allow_shared_fallback,
        )
        if not isinstance(res, LLMResponse):
            raise TypeError("The LLM provider returned a stream for a non-streaming planning request.")

        content = str(res.content).strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        elif "{" in content and "}" in content:
            content = content[content.find("{"):content.rfind("}") + 1].strip()

        data = json.loads(content)
        tool = data.get("tool", "sql_tool")
        desc = data.get("description", "Execute analytical query")

        if tool == "sql_tool" and data.get("sql"):
            sql_text = data["sql"].strip()
            chart_type = data.get("chart_type", "none")
            step1 = PlanStep(
                id="step_1",
                tool="sql_tool",
                description=desc,
                parameters={"sql": sql_text},
            )
            steps = [step1]
            if chart_type and chart_type != "none":
                step2 = PlanStep(
                    id="step_2",
                    tool="chart_tool",
                    description=f"Generate {chart_type} visualization",
                    dependencies=["step_1"],
                    parameters={"chart_type": chart_type},
                )
                steps.append(step2)
            dag = PlanDAG(steps=steps)
            dag.validate_dag()
            return dag

        elif tool == "anomaly_tool":
            col = "revenue" if "revenue" in question.lower() else "quantity"
            return PlanDAG(steps=[
                PlanStep(
                    id="step_1",
                    tool="anomaly_tool",
                    description="Detect statistical anomalies using ensemble methods",
                    parameters={"column": col},
                )
            ])

        elif tool == "forecast_tool":
            return PlanDAG(steps=[
                PlanStep(
                    id="step_1",
                    tool="forecast_tool",
                    description="Compute Holt-Winters projection with confidence intervals",
                    parameters={"horizon": 3},
                )
            ])

        elif tool == "hypothesis_tool":
            return PlanDAG(steps=[
                PlanStep(
                    id="step_1",
                    tool="hypothesis_tool",
                    description="Investigate root cause and rank candidate drivers",
                    parameters={"target_period": "2024-03", "dimension": "region"},
                )
            ])

        return None

    async def narrate_with_llm(
        self,
        question: str,
        lane: str,
        ledger: EvidenceLedger,
        user_id: int,
        user_key: Any = None,
        allow_shared_fallback: bool = True,
    ) -> FinalNarrative | None:
        """Compose grounded, executive narrative using active live LLM strictly from Evidence Ledger."""
        if not ledger.entries:
            return None

        ledger_summary = []
        for entry in ledger.entries:
            preview = entry.result_preview
            if isinstance(preview, list) and len(preview) > 10:
                preview = preview[:10]
            ledger_summary.append({
                "step_id": entry.step_id,
                "tool": entry.tool,
                "code": entry.code,
                "result_preview": preview,
                "row_count": entry.row_count,
            })

        prompt = f"""You are Lumen's Grounded Business Analyst Narrator.
User Question: "{question}"
Evidence Ledger (the immutable source of truth):
{json.dumps(ledger_summary, indent=2, default=str)}

Strict Principles (Rule P1 & P2):
1. The LLM NEVER computes or invents numbers. You may ONLY cite numbers that exist in the Evidence Ledger.
2. Format numbers nicely ($X,XXX.XX or percentages).
3. Provide a clear direct answer, business insight, and citation of how the data was queried.
4. Suggest 3 relevant analytical follow-up questions.

Respond ONLY with valid JSON conforming to:
{{
  "direct_answer": "...",
  "business_insight": "...",
  "how_i_got_this": "...",
  "suggested_followups": ["...", "...", "..."]
}}"""

        res = await self.llm_router.complete(
            messages=[LLMMessage(role="user", content=prompt)],
            tier="strong",
            user_id=user_id,
            user_key=user_key,
            allow_shared_fallback=allow_shared_fallback,
        )
        if not isinstance(res, LLMResponse):
            raise TypeError("The LLM provider returned a stream for a non-streaming narration request.")

        content = str(res.content).strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        elif "{" in content and "}" in content:
            content = content[content.find("{"):content.rfind("}") + 1].strip()

        data = json.loads(content)

        chart_spec = None
        sql_code = None
        pandas_code = None
        for entry in ledger.entries:
            if entry.tool == "chart_tool" and isinstance(entry.result_preview, dict):
                chart_spec = entry.result_preview
            if entry.tool == "sql_tool":
                sql_code = entry.code
            if entry.tool == "pandas_tool":
                pandas_code = entry.code

        return FinalNarrative(
            direct_answer=str(data.get("direct_answer", "")),
            business_insight=str(data.get("business_insight", "")),
            how_i_got_this=str(data.get("how_i_got_this", "")),
            chart_spec=chart_spec,
            confidence="High",
            suggested_followups=list(data.get("suggested_followups", []))[:3],
            sql_code=sql_code,
            pandas_code=pandas_code,
        )

    async def run(
        self,
        question: str,
        session_id: str,
        user_id: int,
        trace_id: str,
        memory: AgentMemory | None = None,
        governor: BudgetGovernor | None = None,
        user_key: Any = None,
        allow_shared_fallback: bool = True,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute question pipeline emitting live SSE events."""
        start_time = time.perf_counter()
        budget = governor or BudgetGovernor()
        settings = get_settings()

        # Check if live LLM APIs are active
        is_live = (settings.llm_provider != "mock" and settings.app_env != "test") or (
            user_key is not None and getattr(user_key, "status", None) == "active"
        )
        if settings.app_env.lower() == "production" and not is_live:
            yield AgentEvent(
                event_type="error", trace_id=trace_id,
                payload={"message": "No real AI provider is available. Configure a provider key before asking questions."},
            )
            yield AgentEvent(event_type="done", trace_id=trace_id, payload={"status": "error"})
            return

        # Step 1: Context and Entity Resolution
        resolved_question, extracted_entities = self.context_resolver.resolve(question, memory)

        # Step 3: Intent Routing
        route = self.router.route(resolved_question)

        # Handle Clarify Lane (ambiguous input -> ask 1 precise question with tappable options)
        if route.lane == "clarify":
            yield AgentEvent(event_type="route", trace_id=trace_id, payload={"lane": route.lane, "confidence": route.confidence, "reason": route.reason, "resolved_question": resolved_question})
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
            yield AgentEvent(event_type="done", trace_id=trace_id, payload={"status": "clarification_needed"})
            return

        # Prepare Per-Tenant Isolated Warehouse & Tools
        db_path, allowed_tables = ensure_user_warehouse(user_id)
        if not allowed_tables:
            yield AgentEvent(event_type="error", trace_id=trace_id, payload={"message": "Upload a dataset before asking a question."})
            yield AgentEvent(event_type="done", trace_id=trace_id, payload={"status": "error"})
            return
        schema_summary = _get_table_schema_summary(db_path, allowed_tables)
        schema_hash = hashlib.sha256(f"{user_id}:{schema_summary}".encode()).hexdigest()
        cache_key = self.cache.generate_cache_key(resolved_question, schema_hash)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            yield AgentEvent(event_type="route", trace_id=trace_id, payload={"lane": "cache_hit", "confidence": 1.0, "reason": "Verified tenant schema cache match"})
            yield AgentEvent(event_type="verify", trace_id=trace_id, payload={"confidence": "High", "reasons": ["Answer retrieved from verified cache for the current tenant schema"]})
            if cached_result.get("chart_spec"):
                yield AgentEvent(event_type="chart", trace_id=trace_id, payload={"chart_spec": cached_result["chart_spec"]})
            yield AgentEvent(event_type="final", trace_id=trace_id, payload={**cached_result, "cached": True})
            yield AgentEvent(event_type="done", trace_id=trace_id, payload={"status": "success", "cached": True})
            return
        yield AgentEvent(event_type="route", trace_id=trace_id, payload={"lane": route.lane, "confidence": route.confidence, "reason": route.reason, "resolved_question": resolved_question})
        tools_registry: dict[str, Any] = {
            "sql_tool": SQLTool(db_path=db_path, allowed_tables=allowed_tables),
            "pandas_tool": PandasTool(),
            "chart_tool": ChartTool(),
            "search_tool": SearchTool(),
            "anomaly_tool": AnomalyTool(),
            "forecast_tool": ForecastTool(),
            "hypothesis_tool": HypothesisTool(),
        }

        # Step 4: Execution Planning (DAG)
        dag: PlanDAG | None = None
        if is_live:
            try:
                dag = await self.plan_with_llm(
                    question=resolved_question,
                    lane=route.lane,
                    allowed_tables=allowed_tables,
                    db_path=db_path,
                    user_id=user_id,
                    user_key=user_key,
                    allow_shared_fallback=allow_shared_fallback,
                )
            except Exception as exc:
                logger.warn("llm_planning_failed_fallback_deterministic", error=str(exc))
                if settings.app_env.lower() == "production" or settings.llm_provider != "mock":
                    yield AgentEvent(event_type="error", trace_id=trace_id, payload={"message": "All configured AI providers failed while planning this analysis."})
                    yield AgentEvent(event_type="done", trace_id=trace_id, payload={"status": "error"})
                    return
                dag = None

        if dag is None:
            schemas: dict[str, list[str]] = {}
            con = duckdb.connect(db_path, read_only=True)
            try:
                for table in allowed_tables:
                    schemas[table] = [str(column[0]) for column in con.execute(f'DESCRIBE "{table}"').fetchall()]
            finally:
                con.close()
            dag = self.planner.plan(resolved_question, route.lane, allowed_tables, schemas)

        yield AgentEvent(
            event_type="plan",
            trace_id=trace_id,
            payload={"dag": dag.model_dump()},
        )

        # Step 5: Concurrent DAG Step Execution with Evidence Ledger
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

        # Check budget governor before proceeding with steps
        exhausted, reason = budget.is_exhausted()
        if exhausted:
            notice = budget.get_degradation_notice(reason or "Budget limit reached")
            yield AgentEvent(
                event_type="final",
                trace_id=trace_id,
                payload={
                    "direct_answer": f"Analysis stopped early due to budget constraints: {reason}.",
                    "business_insight": "Partial analysis rendered under resource governor limit.",
                    "how_i_got_this": "Budget Governor cap reached.",
                    "confidence": "Low",
                    "partial_analysis": True,
                    "degradation_notice": notice,
                    "suggested_followups": ["Refine question scope", "Query specific metric"],
                },
            )
            yield AgentEvent(event_type="done", trace_id=trace_id, payload={"status": "budget_exhausted"})
            return

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
        budget.record_step(tokens=150)

        # Step 6: Draft Narration (Dynamic Live LLM strictly from Evidence Ledger)
        draft_narrative: FinalNarrative | None = None
        if is_live:
            try:
                draft_narrative = await self.narrate_with_llm(
                    question=resolved_question,
                    lane=route.lane,
                    ledger=ledger,
                    user_id=user_id,
                    user_key=user_key,
                    allow_shared_fallback=allow_shared_fallback,
                )
            except Exception as exc:
                logger.warn("llm_narration_failed_fallback_deterministic", error=str(exc))
                if settings.app_env.lower() == "production" or settings.llm_provider != "mock":
                    yield AgentEvent(event_type="error", trace_id=trace_id, payload={"message": "All configured AI providers failed while preparing the answer."})
                    yield AgentEvent(event_type="done", trace_id=trace_id, payload={"status": "error"})
                    return
                draft_narrative = None

        if draft_narrative is None:
            draft_narrative = self.narrator.compose_final(
                question=resolved_question,
                lane=route.lane,
                ledger=ledger,
                confidence="High",
            )

        executed = self.narrator.compose_final(resolved_question, route.lane, ledger)
        draft_narrative.sql_code = executed.sql_code
        draft_narrative.pandas_code = executed.pandas_code
        if route.lane == "code_request":
            draft_narrative.direct_answer = executed.direct_answer

        # Step 7: Verification (Skeptic) - Audit draft answer numbers against Evidence Ledger
        verification = self.verifier.verify(
            draft_answer=draft_narrative.direct_answer,
            ledger=ledger,
        )

        # Apply verification sanitization and confidence tier
        # Code is executable evidence, not a prose claim. Preserve the exact tool code
        # recorded in the ledger; the verifier still checks and scores prose separately.
        if verification.sanitized_answer and route.lane != "code_request":
            draft_narrative.direct_answer = verification.sanitized_answer
        draft_narrative.confidence = verification.confidence

        yield AgentEvent(
            event_type="verify",
            trace_id=trace_id,
            payload=verification.model_dump(),
        )

        # Yield Chart event if chart was produced
        if draft_narrative.chart_spec:
            yield AgentEvent(
                event_type="chart",
                trace_id=trace_id,
                payload={"chart_spec": draft_narrative.chart_spec},
            )

        # Stream narrative tokens
        async for token in self.narrator.stream_tokens(draft_narrative.direct_answer):
            yield AgentEvent(
                event_type="token",
                trace_id=trace_id,
                payload={"delta": token},
            )

        # Yield Final Complete Narrative
        yield AgentEvent(
            event_type="final",
            trace_id=trace_id,
            payload=draft_narrative.model_dump(),
        )

        # Cache only verified, non-Low confidence answers (Rule P2)
        if verification.confidence != "Low":
            self.cache.put(resolved_question, draft_narrative.model_dump(), confidence=verification.confidence, schema_hash=schema_hash)

        # Step 8: Completion event
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
                final_answer=draft_narrative.direct_answer,
                entities=extracted_entities,
                sql_query=draft_narrative.sql_code,
            )
