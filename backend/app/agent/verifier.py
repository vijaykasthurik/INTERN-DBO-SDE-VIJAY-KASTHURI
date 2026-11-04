"""Dual-pass Verifier (skeptic) performing sanity checks, cross-checks, and number grounding."""

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agent.ledger import EvidenceLedger


class VerificationResult(BaseModel):
    """Output of skeptic sanity checks, cross-method numerical audits, and grounding verification."""

    confidence: Literal["High", "Medium", "Low"]
    reasons: list[str] = Field(default_factory=list)
    cross_check_passed: bool = True
    grounded_numbers_ratio: float = 1.0
    ungrounded_numbers: list[float] = Field(default_factory=list)
    sanitized_answer: str = ""
    replan_recommended: bool = False


class Verifier:
    """Sanity checks queries, catches join fanouts, and verifies number grounding against Evidence Ledger."""

    def verify(
        self,
        draft_answer: str,
        ledger: EvidenceLedger,
        sql_result: Any = None,
        pandas_result: Any = None,
    ) -> VerificationResult:
        """Execute skeptic audit over draft response and Evidence Ledger."""
        reasons: list[str] = []
        replan_recommended = False
        cross_check_passed = True

        # 1. Sanity Checks over Ledger
        if not ledger.entries:
            return VerificationResult(
                confidence="Low",
                reasons=["Evidence Ledger is empty; no computational steps recorded."],
                cross_check_passed=False,
                grounded_numbers_ratio=0.0,
                sanitized_answer="No validated evidence available.",
                replan_recommended=True,
            )

        # Check for empty result sets
        for entry in ledger.entries:
            if entry.status == "failed":
                reasons.append(f"Step '{entry.step_id}' failed execution: {entry.error}")
                replan_recommended = True
            elif entry.row_count == 0:
                reasons.append(f"Step '{entry.step_id}' yielded 0 rows.")

            # Join fan-out detection: JOIN query resulting in suspicious row multiplication
            if entry.tool == "sql_tool" and "join" in str(entry.code).lower() and entry.row_count > 50000:
                reasons.append(
                    f"Potential JOIN fan-out detected in step '{entry.step_id}': {entry.row_count} rows produced."
                )
                replan_recommended = True

        # Check for negative revenue in ledger results
        all_ledger_numbers = ledger.get_all_numbers()
        for num in all_ledger_numbers:
            if num < 0 and "revenue" in draft_answer.lower():
                reasons.append(f"Suspicious negative value ({num}) found in revenue calculation.")
                replan_recommended = True

        # Sanity check: explicit percentage > 100% when describing a share or proportion
        explicit_percentages = re.findall(r"(\d+(?:\.\d+)?)%", draft_answer)
        for p_str in explicit_percentages:
            p_val = float(p_str)
            if p_val > 100.0 and not any(kw in draft_answer.lower() for kw in ["growth", "increase", "spike"]):
                reasons.append(f"Improbable percentage or share value ({p_val}%) detected.")
                replan_recommended = True

        # 2. SQL vs Pandas Cross-Check
        if sql_result is not None and pandas_result is not None:
            try:
                s_val = float(sql_result) if not isinstance(sql_result, (dict, list)) else None
                p_val = float(pandas_result) if not isinstance(pandas_result, (dict, list)) else None
                if s_val is not None and p_val is not None and not math.isclose(s_val, p_val, rel_tol=0.01):
                    cross_check_passed = False
                    reasons.append(
                        f"Numerical disparity between SQL ({s_val}) and Pandas ({p_val}) exceeds 1% tolerance."
                    )
                    replan_recommended = True
            except Exception:
                pass

        # 3. Strict Number Grounding (Rule P1: LLM never invents numbers)
        # Extract all numbers from draft text
        cited_number_strings = re.findall(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+", draft_answer)
        cited_numbers: list[float] = []
        for s in cited_number_strings:
            clean = s.replace(",", "")
            try:
                val = float(clean)
                # Ignore small structural integers like 1, 2, 3, 4, 5 in bullets or rankings
                if val > 10.0 or "." in s:
                    cited_numbers.append(round(val, 2))
            except ValueError:
                pass

        ungrounded: list[float] = []
        for num in cited_numbers:
            if not ledger.is_number_grounded(num, tolerance=0.05):
                ungrounded.append(num)

        grounded_ratio = 1.0
        if cited_numbers:
            grounded_ratio = (len(cited_numbers) - len(ungrounded)) / len(cited_numbers)

        sanitized_text = draft_answer
        if ungrounded:
            reasons.append(f"Ungrounded numbers detected: {ungrounded} not present in Evidence Ledger.")

            def _redact_ungrounded(match: re.Match[str]) -> str:
                raw = match.group(0)
                clean = raw.replace("$", "").replace(",", "")
                try:
                    val = round(float(clean), 2)
                    if any(math.isclose(val, u, rel_tol=0.01) for u in ungrounded):
                        return "[UNGROUNDED_NUMBER_REMOVED]"
                except ValueError:
                    pass
                return str(raw)

            num_pattern = re.compile(r"\$?[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$?\d+")
            sanitized_text = num_pattern.sub(_redact_ungrounded, draft_answer)

        # 4. Determine Confidence Tier
        confidence: Literal["High", "Medium", "Low"] = "High"
        if replan_recommended or not cross_check_passed or grounded_ratio < 0.7:
            confidence = "Low"
        elif ungrounded or len(reasons) > 0:
            confidence = "Medium"
        else:
            reasons.append("All cited numbers successfully grounded in Evidence Ledger.")

        return VerificationResult(
            confidence=confidence,
            reasons=reasons,
            cross_check_passed=cross_check_passed,
            grounded_numbers_ratio=round(grounded_ratio, 2),
            ungrounded_numbers=ungrounded,
            sanitized_answer=sanitized_text,
            replan_recommended=replan_recommended,
        )
