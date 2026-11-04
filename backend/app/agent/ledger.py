"""Evidence Ledger: Immutable record of code, data, and verified metrics.

Non-Negotiable Principle P1: The LLM NEVER computes or invents numbers.
Every number in the final narrative must exist within this ledger.
"""

import math
import re
from typing import Any

from pydantic import BaseModel, Field


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


class EvidenceLedger(BaseModel):
    """Manages the verifiable ledger for a single analytical question workflow."""

    entries: list[LedgerEntry] = Field(default_factory=list)

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

    def get_all_numbers(self) -> set[float]:
        """Extract all numerical values present across all ledger entries."""
        numbers: set[float] = set()

        def _extract_recursive(val: Any) -> None:
            if isinstance(val, (int, float)):
                if not math.isnan(val) and not math.isinf(val):
                    numbers.add(round(float(val), 2))
            elif isinstance(val, dict):
                for k, v in val.items():
                    _extract_recursive(k)
                    _extract_recursive(v)
            elif isinstance(val, (list, tuple, set)):
                for item in val:
                    _extract_recursive(item)
            elif isinstance(val, str):
                # Search for formatted numbers like "$1,482,900.00" or "34.2%" or "1820"
                matches = re.findall(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+", val)
                for m in matches:
                    clean_str = m.replace(",", "")
                    try:
                        f_val = float(clean_str)
                        numbers.add(round(f_val, 2))
                    except ValueError:
                        pass

        for entry in self.entries:
            _extract_recursive(entry.result_preview)
            numbers.add(round(float(entry.row_count), 2))

        return numbers

    def is_number_grounded(self, num: float, tolerance: float = 0.05) -> bool:
        """Verify whether a proposed number exists in the ledger within tolerance."""
        all_nums = self.get_all_numbers()
        for known in all_nums:
            if math.isclose(known, num, rel_tol=tolerance, abs_tol=tolerance):
                return True
        return False
