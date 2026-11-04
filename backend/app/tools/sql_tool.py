"""DuckDB SQL execution tool with multi-table join awareness and validation."""

from typing import Any

import duckdb

from app.safety.sql_validator import SQLValidator


class SQLTool:
    """Executes validated SQL against per-user read-only DuckDB databases."""

    def __init__(self, db_path: str, allowed_tables: list[str]) -> None:
        self.db_path = db_path
        self.validator = SQLValidator(allowed_tables=allowed_tables)

    def execute(self, sql_query: str) -> dict[str, Any]:
        """Validate query and execute against DuckDB read-only connection."""
        sanitized_sql = self.validator.validate_and_sanitize(sql_query)
        con = duckdb.connect(self.db_path, read_only=True)
        try:
            rel = con.sql(sanitized_sql)
            df = rel.df()
            return {
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "row_count": len(df),
            }
        finally:
            con.close()
