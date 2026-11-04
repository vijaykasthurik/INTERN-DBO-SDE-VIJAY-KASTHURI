"""Budget governor: caps token, step, and execution time per question."""

from typing import Any


class BudgetGovernor:
    """Enforces execution budgets and triggers graceful partial degradation when exhausted."""

    def __init__(self, max_steps: int = 10, max_tokens: int = 8000, max_duration_sec: float = 30.0) -> None:
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.max_duration_sec = max_duration_sec

    def check_budget(self, current_steps: int, used_tokens: int, elapsed_sec: float) -> dict[str, Any]:
        """Assess if remaining budget allows continuing full execution."""
        within_budget = (
            current_steps < self.max_steps
            and used_tokens < self.max_tokens
            and elapsed_sec < self.max_duration_sec
        )
        return {
            "within_budget": within_budget,
            "current_steps": current_steps,
            "max_steps": self.max_steps,
        }
