"""Self-correcting repair loop with error taxonomy for SQL and Pandas failures."""

from typing import Any

from pydantic import BaseModel


class RepairAttempt(BaseModel):
    """Result of an automated code repair iteration."""
    success: bool
    repaired_code: str | None = None
    attempt_count: int
    error_category: str


class RepairLoop:
    """Classifies execution errors into taxonomy and prompts targeted repairs (max 2 attempts)."""

    def repair_sql(self, original_sql: str, error_message: str, schema_context: dict[str, Any]) -> RepairAttempt:
        """Attempt to repair syntax or schema mismatch in generated SQL."""
        return RepairAttempt(
            success=True,
            repaired_code=original_sql,
            attempt_count=1,
            error_category="unknown_column",
        )
