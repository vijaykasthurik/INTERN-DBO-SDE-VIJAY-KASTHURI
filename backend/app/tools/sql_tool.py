"""DuckDB SQL execution tool with validation, timeout enforcement, and error taxonomy for repair."""

import concurrent.futures
import time
from typing import Any

import duckdb

from app.safety.sql_validator import SQLValidator


class SQLExecutionError(Exception):
    """Raised when an SQL execution fails at the DuckDB engine level."""

    def __init__(self, message: str, error_type: str = "generic_error", sql: str = "") -> None:
        super().__init__(message)
        self.error_type = error_type
        self.sql = sql


def classify_sql_error(error_msg: str) -> str:
    """Classify DuckDB error message into repair loop taxonomy categories."""
    msg = error_msg.lower()
    if "does not have a column" in msg or "column not found" in msg or "referenced column" in msg:
        return "unknown_column"
    if "ambiguous column" in msg or "column reference is ambiguous" in msg:
        return "ambiguous_column"
    if "table" in msg and ("does not exist" in msg or "not found" in msg):
        return "table_not_found"
    if "type mismatch" in msg or "cannot cast" in msg or "conversion" in msg:
        return "type_error"
    if "syntax error" in msg or "parser error" in msg:
        return "syntax_error"
    if "timed out" in msg or "timeout" in msg:
        return "timeout"
    return "execution_error"


class SQLTool:
    """Executes validated SQL against per-user read-only DuckDB databases."""

    def __init__(
        self,
        db_path: str,
        allowed_tables: list[str] | set[str] | None = None,
        max_limit: int = 1000,
        timeout_sec: float = 15.0,
        enforce_relationships: bool = False,
    ) -> None:
        self.enforce_relationships = enforce_relationships
        self.db_path = db_path
        self.validator = SQLValidator(allowed_tables=allowed_tables, max_limit=max_limit)
        self.timeout_sec = timeout_sec

    def execute(self, sql_query: str) -> dict[str, Any]:
        """Validate query and execute against DuckDB read-only connection with timeout protection."""
        start_time = time.perf_counter()
        sanitized_sql = self.validator.validate_and_sanitize(sql_query)

        join_checks: list[dict[str, Any]] = []
        if self.enforce_relationships:
            from app.safety.relationship_guard import validate_base_joins
            join_checks = validate_base_joins(sanitized_sql,self.db_path,list(self.validator.allowed_tables or []))
        con = duckdb.connect(self.db_path, read_only=True)
        try:

            def _run_query() -> Any:
                rel = con.sql(sanitized_sql)
                return rel.df()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_query)
                try:
                    df = future.result(timeout=self.timeout_sec)
                except concurrent.futures.TimeoutError as e:
                    con.interrupt()
                    raise SQLExecutionError(
                        f"Query execution timed out after {self.timeout_sec}s",
                        error_type="timeout",
                        sql=sanitized_sql,
                    ) from e
                except Exception as e:
                    error_type = classify_sql_error(str(e))
                    raise SQLExecutionError(str(e), error_type=error_type, sql=sanitized_sql) from e

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return {
                "success": True,
                "join_checks": join_checks,
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "row_count": len(df),
                "sanitized_sql": sanitized_sql,
                "runtime_ms": round(elapsed_ms, 2),
                "error": None,
            }
        finally:
            con.close()
