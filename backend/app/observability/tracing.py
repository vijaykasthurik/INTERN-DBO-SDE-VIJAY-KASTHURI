"""End-to-end question execution tracing and SQLite persistence."""

from pydantic import BaseModel


class ExecutionTrace(BaseModel):
    """Detailed trace metadata for a single user question execution."""
    trace_id: str
    user_id: int
    session_id: str
    question: str
    lane: str
    provider: str
    duration_ms: float
    total_tokens: int
    cost_usd: float
    cache_hit: bool = False
    verifier_confidence: str = "High"


class TraceManager:
    """Records and queries question lifecycle execution traces."""

    def record_trace(self, trace: ExecutionTrace) -> None:
        """Persist execution trace."""
        pass
