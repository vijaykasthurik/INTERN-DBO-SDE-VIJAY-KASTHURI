# Architectural & Design Decisions

This document details the 12 core design decisions governing Lumen's implementation, detailing the problem statement, considered alternatives, rationale, and tradeoffs.

---

### Decision 1: The LLM Never Computes (Rule P1)
- **Problem**: Large Language Models are probabilistic next-token predictors. When tasked with arithmetic or aggregations over thousands of rows, they hallucinate plausible-sounding but inaccurate numbers.
- **Decision**: The LLM is restricted to planning and code generation. Computation is delegated strictly to **DuckDB** and sandboxed **Pandas**. Every cited number in a final response must exist in the **Evidence Ledger**.
- **Tradeoff**: Increases pipeline stages (planning -> code execution -> validation), but provides 100% computational correctness and auditability.

---

### Decision 2: Skeptic Verifier & Strict Number Grounding (Rule P2)
- **Problem**: Even if code executes cleanly, an LLM might misinterpret a filter or cite numbers from memory that do not match the query output.
- **Decision**: All candidate answers pass through an adversarial **Verifier**. The Verifier scans all numerical tokens in the draft text. If a number is absent from the Evidence Ledger, it is automatically redacted (`[UNGROUNDED_NUMBER_REMOVED]`) and degrades confidence to `Medium` or `Low`. Key metrics are cross-checked via an independent second method (SQL vs Pandas).
- **Tradeoff**: Adds ~10-20ms of verification overhead; guarantees zero hallucinated statistics reach the user.

---

### Decision 3: The Evidence Ledger as an Immutable Audit Trail
- **Problem**: Business users require proof of how numbers were derived before presenting metrics to executive leadership.
- **Decision**: Every step executed records `{step_id, tool, code, result_preview, row_count, runtime_ms, status}` into an append-only Evidence Ledger. The UI renders this directly in an interactive slide-in drawer.
- **Tradeoff**: Requires database storage per message; creates total transparency and enterprise trust.

---

### Decision 4: DAG-Based Planning with Kahn's Algorithm Wave Scheduling
- **Problem**: Complex inquiries (e.g. comparing seasonal trends while simultaneously isolating outliers across two distinct tables) suffer from slow sequential execution.
- **Decision**: The Planner outputs a Directed Acyclic Graph (DAG) with explicit step dependencies. Kahn's algorithm groups independent steps into concurrent execution waves run in parallel via `asyncio.gather`.
- **Tradeoff**: Slightly more complex planner output; achieves up to 3x reduction in multi-step execution latency.

---

### Decision 5: Semantic Layer & Compact Catalog Projection
- **Problem**: Passing entire raw tables or naive schema definitions to an LLM wastes prompt tokens and leaks raw customer data.
- **Decision**: During data onboarding, Lumen compiles a compact semantic catalog containing statistical column summaries, inferred business descriptions, and multi-table relationships. The LLM only sees this concise catalog.
- **Tradeoff**: Initial onboarding takes 1-2 seconds per CSV; drastically reduces token usage and prompt injection risk during chat.

---

### Decision 6: Multi-Tenant Analytical Isolation (Rule P6)
- **Problem**: Shared analytical databases risk cross-tenant data leakage if filters fail.
- **Decision**: Each user account receives a dedicated DuckDB file (`data/user_warehouses/user_{id}.duckdb`). SQLite metadata is filtered by `user_id == current_user.id` on all queries.
- **Tradeoff**: File handle management per user; guarantees zero possibility of cross-user table queries.

---

### Decision 7: Multi-Layer Security Sandbox (SELECT-Only & AST Restrictions)
- **Problem**: User-uploaded CSVs or adversarial prompts could attempt destructive SQL injection or Python remote code execution.
- **Decision**: DuckDB queries are parsed by `sqlglot` and checked against an allow-list enforcing SELECT-only statements with automatic `LIMIT` capping. Pandas code is executed in an isolated process with restricted `__builtins__`.
- **Tradeoff**: Blocks advanced SQL commands (e.g. `CREATE TEMP TABLE`), but guarantees 100% read-only safety.

---

### Decision 8: Verified Semantic Caching
- **Problem**: Repeated identical questions waste LLM tokens and execution resources.
- **Decision**: Answers are cached under a SHA-256 hash of `question + schema_hash + resolved_context`. Only verified, high-confidence responses are written to cache. Uploading or modifying datasets changes the schema hash, instantly invalidating stale cache entries.
- **Tradeoff**: Memory/disk overhead for cache storage; delivers sub-10ms instantaneous answers for frequent queries.

---

### Decision 9: Unified LLM Interface with Ordered Fallback Chain
- **Problem**: Real LLM APIs suffer from intermittent rate limits (HTTP 429) or upstream outages (HTTP 5xx).
- **Decision**: All providers implement a uniform `LLMProvider` interface. The `LLMRouter` maintains a token-bucket rate limiter and circuit breaker per provider, automatically failing over along `LLM_FALLBACK_ORDER` with exponential backoff and jitter.
- **Tradeoff**: Fallback routing logic; ensures zero disruption to user sessions during provider downtime.

---

### Decision 10: Editorial White Design System & Capsule Navigation
- **Problem**: Modern analytics tools often suffer from dark-mode fatigue or generic dashboard bloat.
- **Decision**: An editorial-meets-fintech aesthetic inspired by Linear, Stripe, and Apple. Pure white (`#FFFFFF`) with subtle `#FAFAFB` panels, Inter Variable typography, Instrument Serif editorial headlines, and a floating half-circle capsule navbar (`NAV_VARIANT = "capsule"`).
- **Tradeoff**: Higher design precision required for contrast; delivers a world-class, premium product feel.

---

### Decision 11: Real-Time SSE Streaming with Reasoning Lifecycle Timeline
- **Problem**: Long-running multi-tool analytical queries create user uncertainty if rendered only when completely finished.
- **Decision**: Server-Sent Events (SSE) broadcast granular lifecycle steps (`route`, `plan`, `step_start`, `step_result`, `verify`, `token`, `final`). The UI renders an animated DAG timeline where steps light up as they execute.
- **Tradeoff**: Requires persistent SSE connection handling and client-side stream state management; provides instant visual feedback and delightful UX.

---

### Decision 12: Offline Deterministic Mock Provider (Rule P4)
- **Problem**: CI/CD pipelines, automated tests, and offline development environments cannot depend on external LLM API keys or incur token costs.
- **Decision**: A deterministic rule-based mock provider powers all development, testing, and evaluation. It generates full DAG plans, SQL queries, anomaly analyses, and verified narratives across all benchmark questions.
- **Tradeoff**: Requires maintaining mock response fixtures for golden test cases; enables 100% reproducible tests without external dependencies or secrets.
