"""Three-tier memory hierarchy: working memory, session history, and semantic memory."""

from typing import Any


class AgentMemory:
    """Maintains active working entities, turn summaries, and entity resolutions."""

    def __init__(self) -> None:
        self.working_entities: dict[str, Any] = {}
        self.turn_history: list[dict[str, Any]] = []

    def update_entities(self, new_entities: dict[str, Any]) -> None:
        """Update active working memory entities."""
        self.working_entities.update(new_entities)
