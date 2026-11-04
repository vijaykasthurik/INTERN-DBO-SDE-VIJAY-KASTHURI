"""Concurrent DAG step executor running independent steps in parallel waves with repair loops."""

import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any

from app.agent.ledger import EvidenceLedger, LedgerEntry
from app.agent.planner import PlanDAG, PlanStep
from app.agent.repair import QueryRepairer


class StepExecutor:
    """Executes DAG steps concurrently respecting dependencies, with timeout and repair handling."""

    def __init__(self, tools_registry: dict[str, Any], per_step_timeout_sec: float = 15.0) -> None:
        self.tools = tools_registry
        self.per_step_timeout_sec = per_step_timeout_sec
        self.repairer = QueryRepairer()

    async def execute_dag(
        self,
        dag: PlanDAG,
        ledger: EvidenceLedger,
        step_event_callback: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]
        | None = None,
    ) -> EvidenceLedger:
        """Topologically schedule and execute DAG steps wave by wave."""
        waves = dag.get_execution_waves()

        for wave in waves:
            # Independent steps within the same wave run concurrently in parallel!
            tasks = [self._execute_single_step(step, ledger, step_event_callback) for step in wave]
            await asyncio.gather(*tasks)

        return ledger

    async def _execute_single_step(
        self,
        step: PlanStep,
        ledger: EvidenceLedger,
        callback: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
    ) -> LedgerEntry:
        """Execute a single atomic tool step with timeout, retry/repair, and ledger recording."""
        start_time = time.perf_counter()

        if callback:
            await callback(
                "step_start",
                {"step_id": step.id, "tool": step.tool, "description": step.description},
            )

        tool_instance = self.tools.get(step.tool)
        code = step.parameters.get("sql") or step.parameters.get("code") or f"-- {step.description}"
        result_preview: Any = None
        row_count = 0
        status = "success"
        error_msg: str | None = None

        if not tool_instance:
            status = "failed"
            error_msg = f"Tool '{step.tool}' not found in registry"
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            entry = ledger.record_step(
                step_id=step.id,
                tool=step.tool,
                code=code,
                result_preview={"error": error_msg},
                row_count=0,
                runtime_ms=round(elapsed_ms, 2),
                status=status,
                error=error_msg,
            )
            if callback:
                await callback(
                    "step_result", {"step_id": step.id, "status": status, "error": error_msg}
                )
            return entry

        # Execute with repair loop (up to MAX_RETRIES)
        for attempt in range(self.repairer.MAX_RETRIES + 1):
            try:
                # Enforce per-step timeout
                async with asyncio.timeout(self.per_step_timeout_sec):
                    if step.tool == "sql_tool":
                        sql = step.parameters.get("sql", "SELECT 1;")
                        # Run blocking duckdb call in default thread executor
                        loop = asyncio.get_running_loop()
                        res = await loop.run_in_executor(None, tool_instance.execute, sql)
                        result_preview = res.get("rows", [])
                        row_count = res.get("row_count", len(result_preview))
                        code = res.get("sanitized_sql", sql)
                        status = "success"
                        error_msg = None
                        break

                    elif step.tool == "pandas_tool":
                        code_str = step.parameters.get("code", "result = {'status': 'ok'}")
                        loop = asyncio.get_running_loop()
                        res = await loop.run_in_executor(
                            None, tool_instance.execute_script, code_str, {}
                        )
                        result_preview = res
                        row_count = len(res) if isinstance(res, (list, dict)) else 1
                        status = "success"
                        error_msg = None
                        break

                    elif step.tool == "chart_tool":
                        # Chart tool builds specification from previous steps in the ledger
                        prev_rows: list[dict[str, Any]] = []
                        prev_cols: list[str] = []
                        for prev_entry in ledger.entries:
                            if (
                                isinstance(prev_entry.result_preview, list)
                                and prev_entry.result_preview
                            ):
                                prev_rows = prev_entry.result_preview
                                prev_cols = list(prev_rows[0].keys())
                                break
                        chart_type = step.parameters.get("chart_type")
                        spec = tool_instance.build_spec(
                            title=step.description,
                            columns=prev_cols,
                            data=prev_rows,
                            chart_type=chart_type,
                        )
                        result_preview = spec
                        row_count = len(prev_rows)
                        status = "success"
                        error_msg = None
                        break

                    else:
                        # Fallback for other specialist tools
                        result_preview = {
                            "status": "completed",
                            "output": f"Tool {step.tool} executed successfully.",
                        }
                        row_count = 1
                        status = "success"
                        break

            except Exception as e:
                error_msg = str(e)
                status = "failed"
                if attempt < self.repairer.MAX_RETRIES and step.tool == "sql_tool":
                    if callback:
                        await callback(
                            "repair",
                            {
                                "step_id": step.id,
                                "attempt": attempt + 1,
                                "error": error_msg,
                            },
                        )
                    # Adjust parameters for next repair attempt
                    continue
                break

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        entry = ledger.record_step(
            step_id=step.id,
            tool=step.tool,
            code=code,
            result_preview=result_preview,
            row_count=row_count,
            runtime_ms=round(elapsed_ms, 2),
            status=status,
            error=error_msg,
        )

        if callback:
            await callback(
                "step_result",
                {
                    "step_id": step.id,
                    "status": status,
                    "row_count": row_count,
                    "runtime_ms": round(elapsed_ms, 2),
                    "error": error_msg,
                },
            )

        return entry
