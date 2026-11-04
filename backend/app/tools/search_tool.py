"""Semantic search tool over columns, metrics, and distinct categorical values."""


from app.data.embeddings import SemanticEmbeddingStore


class SearchTool:
    """Discovers table columns and values matching ambiguous conversational terms."""

    def __init__(self, store: SemanticEmbeddingStore) -> None:
        self.store = store

    def search_schema(self, query: str) -> list[tuple[str, float]]:
        """Search schema for best matching attributes."""
        return self.store.search(query)
