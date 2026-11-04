"""Verified-answer cache with schema-hash invalidation, TTL enforcement, and hit/miss metrics."""

import hashlib
import time
from typing import Any

from pydantic import BaseModel, Field


class CachedAnswer(BaseModel):
    """Payload stored in verified semantic cache."""

    cache_key: str
    question: str
    schema_hash: str
    answer_payload: dict[str, Any]
    confidence: str
    created_at: float = Field(default_factory=time.time)
    expires_at: float


class VerifiedAnswerCache:
    """Caches only verified, High/Medium-confidence answers with schema-hash invalidation."""

    def __init__(self, default_ttl_sec: int = 3600) -> None:
        self.default_ttl_sec = default_ttl_sec
        self._store: dict[str, CachedAnswer] = {}
        self.hits: int = 0
        self.misses: int = 0

    @staticmethod
    def generate_cache_key(question: str, schema_hash: str = "") -> str:
        """Create deterministic SHA-256 cache key."""
        raw = f"{question.strip().lower()}::{schema_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> dict[str, Any] | None:
        """Retrieve verified cached answer if unexpired."""
        entry = self._store.get(cache_key)
        if not entry:
            self.misses += 1
            return None

        # Check TTL expiration
        if time.time() > entry.expires_at:
            del self._store[cache_key]
            self.misses += 1
            return None

        self.hits += 1
        return entry.answer_payload

    def put(
        self,
        question: str,
        answer_payload: dict[str, Any],
        confidence: str,
        schema_hash: str = "default",
        ttl_sec: int | None = None,
    ) -> bool:
        """Store answer in cache ONLY if confidence is High or Medium (Rule P2)."""
        # Never cache Low-confidence or unverified answers
        if confidence.lower() == "low":
            return False

        ttl = ttl_sec or self.default_ttl_sec
        cache_key = self.generate_cache_key(question, schema_hash)

        self._store[cache_key] = CachedAnswer(
            cache_key=cache_key,
            question=question,
            schema_hash=schema_hash,
            answer_payload=answer_payload,
            confidence=confidence,
            expires_at=time.time() + ttl,
        )
        return True

    def invalidate_schema(self, schema_hash: str) -> int:
        """Invalidate all cached answers associated with a modified dataset schema."""
        keys_to_remove = [k for k, v in self._store.items() if v.schema_hash == schema_hash]
        for k in keys_to_remove:
            del self._store[k]
        return len(keys_to_remove)

    def get_metrics(self) -> dict[str, Any]:
        """Report cache performance statistics."""
        total_requests = self.hits + self.misses
        hit_rate = round(self.hits / total_requests, 3) if total_requests > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_cached_entries": len(self._store),
        }
