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
        self.tools_registry = tools_registry
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
                    if step.tool == "overview_tool":
                        loop = asyncio.get_running_loop()
                        result_preview = await loop.run_in_executor(None, tool_instance.execute)
                        row_count = len(result_preview["tables"])
                        code = "\n".join(result_preview["queries"])
                        status = "success"
                        error_msg = None
                        break
                    elif step.tool == "sql_tool":
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
                        sql_tool = self.tools_registry.get("sql_tool")
                        if sql_tool is None:
                            raise ValueError("No authenticated warehouse is available for Pandas.")
                        dataframes = tool_instance.load_dataframes(sql_tool.db_path,sorted(sql_tool.validator.allowed_tables or []))
                        loop = asyncio.get_running_loop()
                        res = await loop.run_in_executor(
                            None, tool_instance.execute_script, code_str, dataframes
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

                    elif step.tool == "anomaly_tool":
                        import pandas as pd
                        df = pd.DataFrame()
                        sql_tool = self.tools_registry.get("sql_tool")
                        if sql_tool is not None and hasattr(sql_tool, "db_path"):
                            db_p = sql_tool.db_path
                            import duckdb
                            tables = sorted(getattr(sql_tool.validator, "allowed_tables", set()))
                            if tables:
                                con = duckdb.connect(db_p, read_only=True)
                                try:
                                    df = con.execute(f'SELECT * FROM "{tables[0]}"').df()
                                finally:
                                    con.close()
                        if df.empty:
                            for prev_entry in ledger.entries:
                                if isinstance(prev_entry.result_preview, list) and prev_entry.result_preview:
                                    df = pd.DataFrame(prev_entry.result_preview)
                                    break

                        numeric_cols = list(df.select_dtypes(include="number").columns)
                        target_col = step.parameters.get("target_column") or next(
                            (name for name in ("revenue", "unit_price", "amount", "price") if name in numeric_cols),
                            numeric_cols[0] if numeric_cols else None,
                        )
                        if target_col is None:
                            raise ValueError("No numeric column is available for anomaly detection.")
                        id_col = step.parameters.get("id_column") or next(
                            (name for name in ("order_id", "id") if name in df.columns),
                            df.columns[0] if len(df.columns) else "id",
                        )
                        res = tool_instance.detect_anomalies(df, target_column=target_col, id_column=id_col)
                        result_preview = res
                        row_count = res.get("summary", {}).get("outliers_detected", len(res.get("outliers", [])))
                        code = f"tool.detect_anomalies(df, target_column='{target_col}', id_column='{id_col}')"
                        status = "success"
                        error_msg = None
                        break

                    elif step.tool == "forecast_tool":
                        rows = []
                        sql_tool = self.tools_registry.get("sql_tool")
                        if sql_tool is not None and hasattr(sql_tool, "db_path"):
                            db_p = sql_tool.db_path
                            import duckdb
                            tables = sorted(getattr(sql_tool.validator, "allowed_tables", set()))
                            if tables:
                                con = duckdb.connect(db_p, read_only=True)
                                try:
                                    columns = con.execute(f'DESCRIBE SELECT * FROM "{tables[0]}"').fetchall()
                                    names = [str(column[0]) for column in columns]
                                    time_key = next((name for name in names if any(token in name.lower() for token in ("date", "time", "month"))), None)
                                    value_key = next(
                                        (name for name in names if name.lower() in {"revenue", "amount", "sales", "total", "price"}),
                                        next((str(column[0]) for column in columns if "INT" in str(column[1]).upper() or "DOUBLE" in str(column[1]).upper() or "DECIMAL" in str(column[1]).upper()), None),
                                    )
                                    if time_key and value_key:
                                        rows = con.execute(
                                            f'SELECT CAST("{time_key}" AS VARCHAR) AS period, SUM("{value_key}") AS value FROM "{tables[0]}" GROUP BY period ORDER BY period'
                                        ).df().to_dict(orient="records")
                                finally:
                                    con.close()
                        if not rows:
                            for prev_entry in ledger.entries:
                                if isinstance(prev_entry.result_preview, list) and prev_entry.result_preview:
                                    rows = prev_entry.result_preview
                                    break

                        horizon = step.parameters.get("horizon", 3)
                        if not rows:
                            raise ValueError("No time series could be derived from the uploaded data.")
                        value_key = "value" if "value" in rows[0] else "revenue"
                        res = tool_instance.generate_forecast(history=rows, periods_ahead=horizon, value_key=value_key)
                        result_preview = res
                        row_count = len(res.get("predictions", []))
                        code = f"tool.generate_forecast(history, periods_ahead={horizon})"
                        status = "success"
                        error_msg = None
                        break

                    elif step.tool == "hypothesis_tool":
                        target_period = step.parameters.get("target_period", "2024-03")
                        target_region = step.parameters.get("target_region", "EMEA")
                        res = tool_instance.investigate_drop(target_period=target_period, target_region=target_region)
                        result_preview = res
                        row_count = len(res.get("ranked_hypotheses", res.get("candidates", [])))
                        code = f"tool.investigate_drop(target_period='{target_period}', target_region='{target_region}')"
                        status = "success"
                        error_msg = None
                        break

                    else:
                        # Fallback for other specialist tools
                        raise ValueError(f"No execution adapter is registered for {step.tool}.")

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
                    sql_curr = step.parameters.get("sql", "")
                    if "list_agg" in sql_curr.lower():
                        import re
                        step.parameters["sql"] = re.sub(r"(?i)\blist_agg\b", "string_agg", sql_curr)
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
                    "tool": step.tool,
                    "code": code,
                    "result_preview": result_preview,
                    "status": status,
                    "row_count": row_count,
                    "runtime_ms": round(elapsed_ms, 2),
                    "error": error_msg,
                },
            )

        return entry
