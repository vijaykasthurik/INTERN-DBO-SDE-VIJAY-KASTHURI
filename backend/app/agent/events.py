"""SSE Event models and serialization for the real-time reasoning timeline."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "route",
    "plan",
    "step_start",
    "step_result",
    "repair",
    "verify",
    "token",
    "chart",
    "final",
    "error",
    "done",
]


class AgentEvent(BaseModel):
    """Standardized SSE payload dispatched during agent execution."""

    event_type: EventType
    trace_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload: dict[str, Any] = Field(default_factory=dict)
