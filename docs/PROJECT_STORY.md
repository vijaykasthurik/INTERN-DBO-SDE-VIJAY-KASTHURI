# Project Story: Engineering Lumen

## 1. The Goal
Enterprise business intelligence tools are caught between two failure modes: traditional dashboards that require rigid schema engineering and SQL experts, and modern LLM chatbots that produce fluent prose but frequently hallucinate numbers, miscalculate floating-point aggregates, and leak raw data into prompt tokens.

Lumen was built to solve this dilemma: an autonomous, production-grade AI Data Analyst web app that lets anyone upload CSV and Excel workbooks and explore their data conversationally, with mathematical certainty and cryptographic evidence grounding.

---

## 2. Architectural Choices

1. **Rule P1: The Model Never Computes, Never Invents Numbers**:
   Language models are probabilistic token predictors, not calculators. In Lumen, the LLM plans operations and translates intent into executable code; DuckDB and Pandas compute the answers. Every number displayed to the user must have an exact origin in the Evidence Ledger.

2. **The PEVN Loop (Plan, Execute, Verify, Narrate)**:
   Instead of a simple conversational loop, Lumen runs an asynchronous pipeline:
   - **Plan**: Translates natural language into a directed acyclic graph (DAG) of specialized tool steps.
   - **Execute**: Schedules DAG waves concurrently via `asyncio.gather` across DuckDB and sandboxed Pandas.
   - **Verify**: An adversarial Skeptic Verifier cross-checks key numbers between independent engines (SQL vs. Pandas) and verifies every numeric claim against the Evidence Ledger.
   - **Narrate**: The narrator streams the final business insight using exclusively ledger-verified facts.

3. **Per-Tenant DuckDB Warehouses**:
   Rather than loading multi-tenant data into a shared database with row-level security or injecting raw files into memory, each user receives an isolated, read-only analytical DuckDB database (`data/user_warehouses/user_{id}.duckdb`). This guarantees zero cross-tenant data leakage and sub-millisecond query performance.

4. **Bring Your Own Key (BYOK) with Smart Fallback**:
   Reviewers and users can connect any of 12+ AI providers (OpenAI, Gemini, Groq, DeepSeek, Anthropic, OpenRouter, etc.). Keys are encrypted with AES-256-GCM and never logged or exposed. If a user key exhausts quota, Lumen transparently falls back to shared server pools without breaking the user experience.

---

## 3. The Hardest Problems Solved

1. **Cryptographic Number Grounding (Rule P2)**:
   Eliminating hallucinations required parsing every drafted numerical claim in the narrative, matching it against the raw cell matrices returned by executed tools, and redacting ungrounded numbers (`[UNGROUNDED_NUMBER_REMOVED]`). This ensures that even when generative models attempt to embellish, ungrounded numbers are systematically stripped before the user sees them.

2. **Multi-Statement and Malicious SQL Defense**:
   Generative models frequently attempt to answer multi-table questions with multiple semicolon-separated statements (e.g., `SELECT * FROM t1; SELECT * FROM t2;`). Lumen implemented an AST sanitization layer using `sqlglot` that enforces single-statement execution, extracts the primary analytical query, and blocks dangerous operations (mutations, file system access, DDL/DML) before execution reaches DuckDB.

3. **Reliable Multi-Table Relational Discovery**:
   Automating cross-file joins without user-defined foreign keys required evaluating column name similarity alongside bidirectional value overlap ratios. Lumen enforces strict join guards: dimension keys must be unique, and the joined row count must exactly match the fact table to prevent join fan-out and distorted aggregates.

4. **Provider-Agnostic Resilience**:
   Different providers return JSON schemas differently. Some wrap responses in markdown fences; others omit required keys or hit rate limits under concurrency. Lumen implemented an ordered fallback router with token-bucket rate limiting, circuit breakers, and bounded structural repair prompts, falling back to deterministic planning if live networks fail.

---

## 4. What I Would Build Next

1. **Semantic Metric Layer with Collaborative Version Control**:
   Allow teams to define standardized business metrics (e.g. Net ARR, Churn, LTV) as version-controlled YAML files with git-style branching and peer review.

2. **Automated Continuous Anomaly Watchdogs**:
   A scheduled background worker that monitors incoming datasets on a cron schedule, detecting drift and sudden trend shifts, and pushing executive briefs to Slack or email.

3. **Natural Language What-If Scenario Modeling**:
   Interactive parameter sliders driven by conversational queries (e.g., "What happens to margin if Europe discounts increase by 4%?").

---

## 5. Commit History Guide & Milestone Tags

Because git history is preserved without rewriting, all progress milestones are permanently tagged on `main`:

| Tag | Phase Name | Core Milestone Summary |
| :--- | :--- | :--- |
| `phase-1-complete` | Bootstrap & Monorepo | Monorepo layout, FastAPI factory, Vite+TS, Docker, Makefile, CI |
| `phase-2-complete` | Data Onboarding & Catalog | Ingestion pipeline, profiler, data quality score, relationship graph, TF-IDF catalog |
| `phase-3-complete` | LLM Layer & Safety | Raw REST providers (Groq, Gemini, OpenRouter), AST SQL validator, Pandas sandbox |
| `phase-4-complete` | PEVN Agent Core | DAG planner, Kahn's algorithm parallel waves, SSE streaming, Evidence Ledger |
| `phase-5-complete` | Advanced Tools & Verifier | Anomaly tool, Holt-Winters forecast, hypothesis tool, skeptic verifier, cache |
| `phase-6-complete` | Reports & Observability | PDF/Markdown exporter, SQLite traces, Prometheus metrics, 32-question eval |
| `phase-7-complete` | Design System & UI | Floating capsule navbar, editorial white tokens, custom UI primitives, landing demo |
| `phase-8-complete` | Workspace & Charts | Three-pane workspace, reasoning timeline, Apache ECharts, Evidence drawer |
| `phase-9-complete` | Dashboards & Polish | Interactive multi-widget dashboard, reports UI, settings, command palette, 404 |
| `phase-10-complete` | Production Containers | Multi-stage Dockerfile, docker-compose, Nginx reverse proxy, security headers |
| `phase-11-complete` | BYOK & Fallback Pool | Declarative provider catalog (12+ LLMs), AES-256-GCM encryption, fallback pool |
| `phase-13-complete` | Fix-Only Audit & Hardening| Real PDF/MD downloads, paginated preview, cascade delete, live provenance |
| `v1.0.0` | Production Release | GitHub CI permanent green, single-statement SQL sanitization, demo media, docs |
