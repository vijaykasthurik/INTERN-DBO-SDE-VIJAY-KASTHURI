"""Prometheus telemetry metrics for request latencies, LLM usage, and verifier audits."""

from prometheus_client import Counter, Histogram, generate_latest

CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

# Metrics definitions
REQUEST_COUNT = Counter("lumen_http_requests_total", "Total HTTP requests", ["endpoint", "method", "status"])
REQUEST_LATENCY = Histogram("lumen_request_duration_seconds", "Request latency in seconds", ["endpoint"])
LLM_CALLS = Counter("lumen_llm_calls_total", "Total LLM completions", ["provider", "tier"])
VERIFIER_REJECTIONS = Counter("lumen_verifier_rejections_total", "Total answers rejected or corrected by Verifier")
CACHE_HITS = Counter("lumen_cache_hits_total", "Total verified answer cache hits")


def get_latest_metrics() -> bytes:
    """Serialize Prometheus metrics registry for scraping."""
    return generate_latest()


__all__ = [
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "LLM_CALLS",
    "VERIFIER_REJECTIONS",
    "CACHE_HITS",
    "get_latest_metrics",
    "CONTENT_TYPE_LATEST",
]
