"""Prometheus telemetry metrics for request latencies, LLM usage, and verifier audits."""

from prometheus_client import Counter, Histogram, generate_latest

CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

# Metrics definitions
REQUEST_COUNT = Counter(
    "lumen_http_requests_total", "Total HTTP requests", ["endpoint", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "lumen_request_duration_seconds", "Request latency in seconds", ["endpoint"]
)
LLM_CALLS = Counter("lumen_llm_calls_total", "Total LLM completions", ["provider", "tier"])
TOKEN_USAGE = Counter("lumen_tokens_total", "Total tokens processed", ["type"])
CACHE_HITS = Counter("lumen_cache_hits_total", "Total verified answer cache hits")
CACHE_REQUESTS = Counter("lumen_cache_requests_total", "Total cache lookups", ["status"])
VERIFIER_REJECTIONS = Counter(
    "lumen_verifier_rejections_total", "Total answers rejected or corrected by Verifier"
)
REPAIR_COUNTS = Counter("lumen_repairs_total", "Total query repair attempts", ["error_type"])


def get_latest_metrics() -> bytes:
    """Serialize Prometheus metrics registry for scraping."""
    return generate_latest()


__all__ = [
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "LLM_CALLS",
    "TOKEN_USAGE",
    "CACHE_HITS",
    "CACHE_REQUESTS",
    "VERIFIER_REJECTIONS",
    "REPAIR_COUNTS",
    "get_latest_metrics",
    "CONTENT_TYPE_LATEST",
]
