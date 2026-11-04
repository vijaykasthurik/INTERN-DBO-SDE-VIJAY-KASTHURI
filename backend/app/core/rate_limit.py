"""Token bucket rate limiter for API endpoints and LLM providers."""

import time


class TokenBucketRateLimiter:
    """In-memory token bucket rate limiter."""

    def __init__(self, capacity: int = 60, refill_rate_per_sec: float = 1.0) -> None:
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate_per_sec)
        self.buckets: dict[str, tuple[float, float]] = {}

    def acquire(self, key: str, tokens: int = 1) -> bool:
        """Attempt to consume tokens. Returns True if granted, False if rate limited."""
        now = time.time()
        current_tokens, last_refill = self.buckets.get(key, (self.capacity, now))

        # Refill tokens
        elapsed = now - last_refill
        current_tokens = min(self.capacity, current_tokens + (elapsed * self.refill_rate))

        if current_tokens >= tokens:
            self.buckets[key] = (current_tokens - tokens, now)
            return True

        self.buckets[key] = (current_tokens, now)
        return False
