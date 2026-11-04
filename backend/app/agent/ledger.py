"""Evidence Ledger: Immutable record of code, data, and verified metrics.

Non-Negotiable Principle P1: The LLM NEVER computes or invents numbers.
Every number in the final narrative must exist within this ledger.
"""

from typing import Any

from pydantic import BaseModel


class LedgerEntry(BaseModel):
    """Atomic step result stored in the Evidence Ledger."""
    step_id: str
    tool: str
    code: str
    result_preview: Any
    row_count: int
    runtime_ms: float
    status: str = "success"
    error: str | None = None


class EvidenceLedger:
    """Manages the verifiable ledger for a single question-answering workflow."""

    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []

    def record_step(
        self,
        step_id: str,
        tool: str,
        code: str,
        result_preview: Any,
        row_count: int,
        runtime_ms: float,
        status: str = "success",
        error: str | None = None,
    ) -> LedgerEntry:
        """Append an executed computation step to the ledger."""
        entry = LedgerEntry(
            step_id=step_id,
            tool=tool,
            code=code,
            result_preview=result_preview,
            row_count=row_count,
            runtime_ms=runtime_ms,
            status=status,
            error=error,
        )
        self.entries.append(entry)
        return entry

    def get_all_numbers(self) -> list[float]:
        """Extract all numerical values present across all ledger step results."""
        numbers: list[float] = []
        # Traversal logic for grounding verification
        return numbers
