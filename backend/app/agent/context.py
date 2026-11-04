"""Context and conversational reference resolution."""

from typing import Any


class ContextResolver:
    """Resolves conversational follow-ups and entity references ("now by month", "why is that low")."""

    def resolve_context(self, question: str, session_history: list[dict[str, Any]]) -> str:
        """Resolve pronoun and contextual elisions into self-contained analytical queries."""
        return question
