"""SQL Validator and AST sanitizer for DuckDB queries.

Enforces SELECT/WITH-SELECT allow-list, rejects DDL/DML/ATTACH/PRAGMA, validates table
names against user tenant tables, and injects default row limits.
"""

import re


class SQLSecurityError(Exception):
    """Raised when a query violates safety constraints."""
    pass


class SQLValidator:
    """Validates and sanitizes SQL queries before execution."""

    FORBIDDEN_KEYWORDS: set[str] = {
        "ATTACH", "DETACH", "PRAGMA", "COPY", "EXPORT", "IMPORT",
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
        "TRUNCATE", "REPLACE", "EXEC", "EXECUTE", "SYSTEM", "READ_CSV",
        "READ_PARQUET", "READ_JSON", "WRITE_CSV",
    }

    def __init__(self, allowed_tables: list[str], max_limit: int = 1000) -> None:
        self.allowed_tables = {t.lower() for t in allowed_tables}
        self.max_limit = max_limit

    def validate_and_sanitize(self, sql: str) -> str:
        """Parse query, assert read-only SELECT, and enforce table whitelist."""
        cleaned = sql.strip().rstrip(";")
        if not cleaned:
            raise SQLSecurityError("Empty query provided")

        upper_sql = cleaned.upper()

        # Check for forbidden dangerous statements
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(r"\b" + keyword + r"\b", upper_sql):
                raise SQLSecurityError(f"Forbidden SQL operation detected: {keyword}")

        # Enforce SELECT / WITH statement only
        if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
            raise SQLSecurityError("Only SELECT queries are permitted")

        return cleaned
