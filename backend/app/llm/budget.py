"""Budget governor: caps token, step, and execution time per question."""

import time
from typing import Any, Literal


class BudgetGovernor:
    """Enforces execution budgets and triggers graceful partial degradation when limits are reached."""

    def __init__(
        self,
        max_steps: int = 8,
        max_tokens: int = 8000,
        max_duration_sec: float = 30.0,
    ) -> None:
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.max_duration_sec = max_duration_sec
        self.start_time = time.perf_counter()
        self.current_steps = 0
        self.used_tokens = 0

    def record_step(self, tokens: int = 0) -> None:
        """Increment step count and token usage."""
        self.current_steps += 1
        self.used_tokens += tokens

    @property
    def elapsed_sec(self) -> float:
        return time.perf_counter() - self.start_time

    def is_exhausted(self) -> tuple[bool, str | None]:
        """Check if any resource budget has been exhausted."""
        if self.current_steps >= self.max_steps:
            return True, f"Maximum step limit reached ({self.max_steps} steps executed)"
        if self.used_tokens >= self.max_tokens:
            return (
                True,
                f"Token budget exhausted ({self.used_tokens}/{self.max_tokens} tokens used)",
            )
        if self.elapsed_sec >= self.max_duration_sec:
            return (
                True,
                f"Execution time budget elapsed ({round(self.elapsed_sec, 1)}s/{self.max_duration_sec}s)",
            )
        return False, None

    def get_degradation_notice(self, reason: str) -> dict[str, Any]:
        """Format honest partial analysis notice for user presentation."""
        return {
            "partial_analysis": True,
            "notice": "Analysis stopped early due to execution budget constraint.",
            "reason": reason,
            "steps_completed": self.current_steps,
            "tokens_consumed": self.used_tokens,
            "elapsed_seconds": round(self.elapsed_sec, 2),
        }

    def select_tier(self, task_complexity: str) -> Literal["fast", "strong"]:
        """Select appropriate LLM model tier based on task type and remaining budget."""
        exhausted, _ = self.is_exhausted()
        if exhausted:
            return "fast"

        # Strong tier for complex reasoning tasks
        if task_complexity in ("investigation", "hypothesis", "root_cause", "deep_anomaly"):
            return "strong"

        # Fast tier for routing, aggregation, code generation, and standard lookups
        return "fast"
