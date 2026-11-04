"""Repair loop and targeted repair prompt generation based on error taxonomy."""

from typing import Any, Literal

ErrorTaxonomyType = Literal[
    "unknown_column",
    "ambiguous_column",
    "table_not_found",
    "type_error",
    "syntax_error",
    "join_fanout",
    "timeout",
    "generic_error",
]


class QueryRepairer:
    """Manages targeted repair iterations for failing analytical queries."""

    MAX_RETRIES = 2

    @staticmethod
    def classify_error(error_msg: str) -> ErrorTaxonomyType:
        """Classify execution error string into targeted repair taxonomy."""
        msg = error_msg.lower()
        if (
            "does not have a column" in msg
            or "column not found" in msg
            or "referenced column" in msg
        ):
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
        if "fanout" in msg or "cartesian" in msg:
            return "join_fanout"
        return "generic_error"

    def build_repair_prompt(
        self,
        failed_code: str,
        error_msg: str,
        attempt: int,
        schema_catalog: dict[str, Any] | None = None,
    ) -> str:
        """Generate a targeted repair prompt addressing the specific error category."""
        error_type = self.classify_error(error_msg)
        schema_info = ""
        if schema_catalog:
            tables = schema_catalog.get("tables", {})
            schema_info = "Available schema columns:\n" + "\n".join(
                f"- Table '{t_name}': {', '.join(t_info.get('columns', []))}"
                for t_name, t_info in tables.items()
            )

        instructions = {
            "unknown_column": "Replace the missing column with the closest matching valid column from the schema.",
            "ambiguous_column": "Qualify all ambiguous column names with their respective table aliases (e.g., sales.customer_id).",
            "table_not_found": "Verify table names against the schema catalog and do not query non-existent tables.",
            "type_error": "Cast data types explicitly using CAST(column AS TYPE) or ensure compatible operands.",
            "syntax_error": "Fix the SQL syntax according to standard DuckDB SQL dialect.",
            "join_fanout": "Add proper join predicates on primary/foreign keys to prevent unintended cartesian expansion.",
            "timeout": "Simplify the query, reduce aggregations, or enforce stricter WHERE filters.",
            "generic_error": "Correct the query to resolve the reported execution error.",
        }

        specific_instruction = instructions.get(error_type, instructions["generic_error"])

        return (
            f"=== SQL REPAIR REQUEST (Attempt {attempt}/{self.MAX_RETRIES}) ===\n"
            f"Error Category: {error_type}\n"
            f"Error Message: {error_msg}\n"
            f"Failing Code:\n```sql\n{failed_code}\n```\n\n"
            f"{schema_info}\n\n"
            f"Targeted Fix: {specific_instruction}\n"
            "Output ONLY the corrected, executable DuckDB SQL query."
        )
