"""End-to-end question execution tracing and SQLite persistence."""

from typing import Any

import structlog
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import ExecutionTrace as DBExecutionTrace
from app.db.session import SessionLocal

logger = structlog.get_logger("lumen.observability.tracing")


class ExecutionTrace(BaseModel):
    """Detailed trace metadata for a single user question execution."""

    trace_id: str
    user_id: int
    session_id: str
    question: str
    lane: str
    provider: str = "mock"
    duration_ms: float
    total_tokens: int = 0
    cost_usd: float = 0.0
    cache_hit: bool = False
    verifier_confidence: str = "High"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceManager:
    """Records and queries question lifecycle execution traces."""

    def __init__(self) -> None:
        self._memory_traces: list[ExecutionTrace] = []

    def record_trace(self, trace: ExecutionTrace, db: Session | None = None) -> None:
        """Persist execution trace to SQLite and emit structured JSON log."""
        self._memory_traces.append(trace)

        # Emit JSON log
        logger.info(
            "execution_trace_recorded",
            trace_id=trace.trace_id,
            user_id=trace.user_id,
            session_id=trace.session_id,
            question=trace.question,
            lane=trace.lane,
            provider=trace.provider,
            duration_ms=trace.duration_ms,
            tokens=trace.total_tokens,
            cost_usd=trace.cost_usd,
            cache_hit=trace.cache_hit,
            verifier_confidence=trace.verifier_confidence,
        )

        # Persist to database if db session provided or available
        target_db = db
        close_needed = False
        if target_db is None:
            try:
                target_db = SessionLocal()
                close_needed = True
            except Exception:
                target_db = None

        if target_db:
            try:
                db_trace = DBExecutionTrace(
                    trace_id=trace.trace_id,
                    user_id=trace.user_id,
                    session_id=trace.session_id,
                    question=trace.question,
                    lane=trace.lane,
                    provider=trace.provider,
                    duration_ms=trace.duration_ms,
                    total_tokens=trace.total_tokens,
                    cost_usd=trace.cost_usd,
                    cache_hit=trace.cache_hit,
                    verifier_confidence=trace.verifier_confidence,
                )
                target_db.add(db_trace)
                target_db.commit()
            except Exception as e:
                logger.warning("failed_to_persist_trace_to_db", error=str(e))
                target_db.rollback()
            finally:
                if close_needed:
                    target_db.close()

    def get_session_traces(self, session_id: str, db: Session | None = None) -> list[ExecutionTrace]:
        """Retrieve recorded traces for a given chat session."""
        if db:
            db_traces = (
                db.query(DBExecutionTrace)
                .filter(DBExecutionTrace.session_id == session_id)
                .order_by(DBExecutionTrace.created_at.asc())
                .all()
            )
            if db_traces:
                return [
                    ExecutionTrace(
                        trace_id=t.trace_id,
                        user_id=t.user_id,
                        session_id=t.session_id,
                        question=t.question,
                        lane=t.lane,
                        provider=t.provider,
                        duration_ms=t.duration_ms,
                        total_tokens=t.total_tokens,
                        cost_usd=t.cost_usd,
                        cache_hit=t.cache_hit,
                        verifier_confidence=t.verifier_confidence,
                    )
                    for t in db_traces
                ]

        return [t for t in self._memory_traces if t.session_id == session_id]
