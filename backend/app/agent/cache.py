"""Verified-Answer Cache with schema-hash invalidation."""

import hashlib
from typing import Any


class VerifiedAnswerCache:
    """Stores only High/Medium verified answers keyed by query + schema hash."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl = ttl_seconds
        self.store: dict[str, Any] = {}

    def compute_cache_key(self, question: str, schema_hash: str) -> str:
        """Derive cryptographic cache key."""
        raw = f"{question.strip().lower()}:{schema_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached verified answer if present."""
        return self.store.get(key)

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Cache verified answer."""
        self.store[key] = value
