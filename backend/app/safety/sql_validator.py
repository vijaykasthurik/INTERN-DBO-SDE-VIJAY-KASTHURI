"""SQL Validator and AST sanitizer for DuckDB queries.

Enforces:
- Single statement only (no multiple/stacked queries)
- SELECT or WITH ... SELECT queries only
- Complete rejection of DDL, DML, ATTACH, DETACH, PRAGMA, COPY, EXPORT, extensions
- Complete rejection of file-reading and OS execution functions (read_csv, read_parquet, read_text, system, glob, etc.)
- Strict table allow-list (including inside CTEs, subqueries, and JOINs)
- Automatic LIMIT injection and capping
"""

import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError


class SQLSecurityError(Exception):
    """Raised when an SQL query violates security or safety constraints."""

    pass


class SQLValidator:
    """Validates and sanitizes SQL queries against DuckDB AST rules."""

    # Disallowed AST expressions
    FORBIDDEN_EXPRESSION_TYPES = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
        exp.Pragma,
        exp.Transaction,
        exp.Commit,
        exp.Rollback,
        exp.Set,
        exp.Copy,
        exp.Attach,
        exp.Detach,
        exp.Export,
        exp.Merge,
        exp.ReadCSV,
        exp.ReadParquet,
    )

    # Disallowed function names (in function calls, Anonymous, and Func nodes)
    FORBIDDEN_FUNCTIONS = {
        "read_csv",
        "read_csv_auto",
        "read_parquet",
        "read_json",
        "read_json_auto",
        "read_ndjson",
        "read_text",
        "read_blob",
        "scan_csv",
        "scan_parquet",
        "glob",
        "system",
        "duckdb_secrets",
        "duckdb_settings",
        "duckdb_memory",
        "load_extension",
        "install_extension",
        "checkpoint",
        "pragma",
        "current_setting",
        "getenv",
    }

    # Keyword patterns that should never appear even in raw or obfuscated syntax
    FORBIDDEN_KEYWORDS = [
        re.compile(r"\bATTACH\b", re.IGNORECASE),
        re.compile(r"\bDETACH\b", re.IGNORECASE),
        re.compile(r"\bCOPY\b", re.IGNORECASE),
        re.compile(r"\bEXPORT\b", re.IGNORECASE),
        re.compile(r"\bIMPORT\b", re.IGNORECASE),
        re.compile(r"\bPRAGMA\b", re.IGNORECASE),
        re.compile(r"\bCHECKPOINT\b", re.IGNORECASE),
        re.compile(r"\bLOAD\s+EXTENSION\b", re.IGNORECASE),
        re.compile(r"\bINSTALL\s+EXTENSION\b", re.IGNORECASE),
        re.compile(r"\bINTO\s+OUTFILE\b", re.IGNORECASE),
        re.compile(r"\bWRITE_CSV\b", re.IGNORECASE),
    ]

    def __init__(
        self, allowed_tables: list[str] | set[str] | None = None, max_limit: int = 1000
    ) -> None:
        self.allowed_tables = (
            {t.lower() for t in allowed_tables} if allowed_tables is not None else None
        )
        self.max_limit = max_limit

    def validate_and_sanitize(self, sql: str) -> str:
        """Validate the SQL query, enforce security rules, and inject LIMIT.

        Returns:
            Sanitized, standardized DuckDB SQL string.
        Raises:
            SQLSecurityError: If any security constraint is violated.
        """
        if not sql or not sql.strip():
            raise SQLSecurityError("Empty query provided")

        cleaned = sql.strip().rstrip(";")

        # Pre-check keyword blacklist to catch unsupported commands that sqlglot might parse as generic commands
        for pattern in self.FORBIDDEN_KEYWORDS:
            if pattern.search(cleaned):
                match = pattern.search(cleaned)
                raise SQLSecurityError(
                    f"Forbidden SQL operation detected: {match.group(0) if match else 'keyword'}"
                )

        # Parse AST with DuckDB dialect
        try:
            parsed_statements = sqlglot.parse(cleaned, read="duckdb")
        except SqlglotError as e:
            raise SQLSecurityError(f"SQL parsing error: {e}") from e

        # Disallow empty or multiple statements
        statements = [stmt for stmt in parsed_statements if stmt is not None]
        if not statements:
            raise SQLSecurityError("Query contained no executable statements")
        if len(statements) > 1:
            raise SQLSecurityError(
                "Multiple statements are strictly forbidden; only single queries are permitted"
            )

        expr = statements[0]

        # Enforce that the root is a SELECT or UNION
        if not isinstance(expr, exp.Select | exp.Union):
            raise SQLSecurityError(
                f"Disallowed statement type: {type(expr).__name__}. Only SELECT queries are permitted."
            )

        # Inspect entire AST tree for forbidden nodes and functions
        for node in expr.walk():
            # Check forbidden AST classes
            if isinstance(node, self.FORBIDDEN_EXPRESSION_TYPES):
                raise SQLSecurityError(f"Forbidden AST expression: {type(node).__name__}")

            # Check function calls
            if isinstance(node, exp.Anonymous):
                func_name = node.name.lower()
                if func_name in self.FORBIDDEN_FUNCTIONS:
                    raise SQLSecurityError(f"Forbidden function call: {node.name}")
            elif isinstance(node, exp.Func):
                func_name = node.sql_name().lower()
                if func_name in self.FORBIDDEN_FUNCTIONS:
                    raise SQLSecurityError(f"Forbidden function call: {func_name}")

        # Discover all Common Table Expression (CTE) names defined in this query
        cte_names = {cte.alias_or_name.lower() for cte in expr.find_all(exp.CTE)}

        # Check table access allowlist if configured
        if self.allowed_tables is not None:
            for table_node in expr.find_all(exp.Table):
                table_name = table_node.name.lower()
                if not table_name:
                    continue
                # If table is a CTE defined within the query, it is allowed
                if table_name in cte_names:
                    continue
                # Otherwise, verify against allowed user tables
                if table_name not in self.allowed_tables:
                    raise SQLSecurityError(
                        f"Access to table '{table_node.name}' is forbidden. Allowed tables: {sorted(self.allowed_tables)}"
                    )

        # Enforce LIMIT injection / capping
        sanitized_expr = self._enforce_limit(expr)

        return sanitized_expr.sql(dialect="duckdb")

    def _enforce_limit(self, expr: exp.Select | exp.Union) -> exp.Select | exp.Union:
        """Inject LIMIT if missing, or clamp to max_limit if excessive."""
        if isinstance(expr, exp.Select):
            limit_node = expr.args.get("limit")
            if limit_node is None:
                return expr.limit(self.max_limit)

            try:
                # Check current limit value
                current_limit = int(limit_node.expression.this)
                if current_limit > self.max_limit:
                    return expr.limit(self.max_limit)
            except (ValueError, AttributeError, TypeError):
                # If non-integer expression, replace with max_limit
                return expr.limit(self.max_limit)

        return expr
