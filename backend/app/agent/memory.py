"""Three-tier memory hierarchy: working memory, session history, and semantic memory."""

import hashlib
from typing import Any

from pydantic import BaseModel, Field


class WorkingMemory(BaseModel):
    """Working memory for the current active turn."""

    active_dataset_id: str | None = None
    resolved_entities: dict[str, Any] = Field(default_factory=dict)
    last_sql_query: str | None = None
    last_question: str | None = None
    last_intent: str | None = None
    last_metric: str | None = None
    last_dimension: str | None = None


class SessionTurn(BaseModel):
    """Single turn in a session conversation."""

    turn_index: int
    user_question: str
    resolved_question: str
    lane: str
    final_answer: str
    entities: dict[str, Any] = Field(default_factory=dict)


class AgentMemory:
    """Manages working memory, session history, turn summaries, and semantic cache."""

    def __init__(self, session_id: str = "") -> None:
        self.session_id = session_id
        self.working = WorkingMemory()
        self.turns: list[SessionTurn] = []
        self.conversation_summary: str = ""
        self._semantic_cache: dict[str, dict[str, Any]] = {}

    def record_turn(
        self,
        user_question: str,
        resolved_question: str,
        lane: str,
        final_answer: str,
        entities: dict[str, Any] | None = None,
        sql_query: str | None = None,
    ) -> None:
        """Record turn outcome into session memory and update working memory."""
        turn_entities = entities or {}
        turn = SessionTurn(
            turn_index=len(self.turns) + 1,
            user_question=user_question,
            resolved_question=resolved_question,
            lane=lane,
            final_answer=final_answer,
            entities=turn_entities,
        )
        self.turns.append(turn)

        # Update working memory
        self.working.last_question = user_question
        self.working.last_intent = lane
        self.working.last_sql_query = sql_query
        self.working.resolved_entities.update(turn_entities)
        if "metric" in turn_entities:
            self.working.last_metric = turn_entities["metric"]
        if "dimension" in turn_entities:
            self.working.last_dimension = turn_entities["dimension"]

        # Summarize older turns if history grows long (> 6 turns)
        if len(self.turns) > 6:
            self._compress_history()

    def _compress_history(self) -> None:
        """Summarize earlier turns into a compact narrative."""
        earlier = self.turns[:-4]
        summary_lines = [
            f"Turn {t.turn_index}: Q: '{t.user_question}' -> Answer: {t.final_answer[:60]}..."
            for t in earlier
        ]
        self.conversation_summary = " | ".join(summary_lines)

    def cache_put(self, cache_key: str, data: dict[str, Any]) -> None:
        """Store verified answer in semantic cache."""
        self._semantic_cache[cache_key] = data

    def cache_get(self, cache_key: str) -> dict[str, Any] | None:
        """Retrieve verified answer from semantic cache."""
        return self._semantic_cache.get(cache_key)

    @staticmethod
    def compute_cache_key(question: str, schema_hash: str = "") -> str:
        """Generate deterministic cache key."""
        raw = f"{question.strip().lower()}::{schema_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
