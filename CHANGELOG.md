# Changelog

All notable changes to the Lumen AI Data Analyst platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-05

### Final Polish and Submission
- **GitHub Actions CI Stabilization**: Fixed Linux-specific type checks (`disallow_subclassing_any = false` for ReportLab flowables), isolated DuckDB test database files to per-session temp directories, and eliminated event loop collision warnings on `sse-starlette`. Both `backend-quality` and `frontend-quality` jobs pass permanently on GitHub Actions.
- **Editorial Design System**: Refined styling across all screens to an editorial-meets-fintech palette with pure white background (`#FFFFFF`), subtle panels (`#FAFAFB`), deep ink text (`#0B0B0F`), restrained emerald accent (`#059669`), solid ink buttons, and zero emojis.
- **Guided Onboarding and Transparency Components**: Added `GuidedOnboardingCard` (5-step onboarding checklist), `UploadSummaryCard` (summary of staged tables, quality scores, and detected joins), `AnswerProvenanceCard` (plain-language explanation of executed queries, runtimes, and cross-checks), and `HelpModal` (5-stage PEVN pipeline diagram and enterprise terminology glossary).
- **Agent Single-Statement Resilience**: Updated query planning to sanitize multi-statement SQL strings from generative models, ensuring single-statement execution compliance with DuckDB AST security rules.
- **Media and Documentation Showcase**: Added Playwright-driven automated recording (`scripts/record_demo.ts`) generating `docs/media/demo.mp4` (H.264, 2.3MB, 24.3s) and `docs/media/demo.gif` (800px wide, 5.6MB), plus 10 full-resolution 1440px desktop screenshots covering all platform states.

---

## [Phase 13] - 2026-11-04
### Fixed and Hardened
- **Report Preview and Downloads**: Converted PDF and Markdown downloads into authentic authenticated blob responses with server-side validation.
- **Pagination and Deletion**: Added paginated row previews (20 rows per page) and cascading deletion of datasets with automatic schema and report cache invalidation.
- **Dashboard Provenance**: Multi-file and single-table dashboards now compute live metrics from DuckDB with embedded query disclosures.

---

## [Phase 12] - 2026-11-04
### Added
- **Multi-Viewport Audit and Requirements Traceability**: Full audit documented in `docs/REQUIREMENTS_TRACEABILITY.md` covering all 14 core assignment requirements and bonus capabilities.
- **Playwright Test Suites**: Added end-to-end browser tests verifying authentication, file uploads, question streaming, and dashboard generation.

---

## [Phase 11] - 2026-11-04
### Added
- **Bring Your Own Key (BYOK) Architecture**: Added declarative provider catalog (`backend/app/llm/catalog.py`) supporting 12+ industry providers (OpenAI, Gemini, Anthropic, Groq, DeepSeek, Mistral, Together, OpenRouter, etc.).
- **Hardware-Grade Key Encryption**: AES-256-GCM encryption at rest with unique 96-bit IVs and zero leakage into JSON logs, traces, or client streams.
- **Smart Fallback Pool**: Transparent fallback to shared server pools when client keys encounter quota or rate limit exhaustion.

---

## [Phase 10] - 2026-11-04
### Added
- **Production Containerization**: Multi-stage Docker builds for backend and frontend with Nginx reverse proxy.
- **Security Hardening**: AST-restricted Pandas sandbox, `sqlglot` SELECT-only AST validation, and strict prompt injection defense.

---

## [Phase 9] - 2026-11-04
### Added
- **Executive Dashboards UI**: Multi-widget responsive dashboard grid with drag-to-reorder layout and fullscreen widget zoom.
- **Executive Reports UI**: PDF and Markdown report builder with custom Matplotlib charts rendered via ReportLab flowables.
- **Settings & Diagnostics**: Real-time provider latency monitoring, tenant data wipeout modal, and custom metric definitions editor.
- **Command Palette**: `Cmd+K` / `Ctrl+K` global command palette with fuzzy navigation.

---

## [Phase 8] - 2026-11-04
### Added
- **Three-Pane Workspace**: Collapsible dataset rail, center conversational thread, and collapsible reasoning timeline.
- **Reasoning Timeline**: Animated visual DAG rendering step runtimes, repair loops, and skeptic verification checks.
- **Evidence Drawer**: Spring-in drawer showing exact executed DuckDB SQL, Pandas equivalent, and raw result rows.
- **Dynamic Charts**: Apache ECharts integration rendering bars, lines, pies, and outlier scatter plots.

---

## [Phase 7] - 2026-11-04
### Added
- **Editorial UI Design System**: Custom primitives (`Button`, `Card`, `Badge`, `Tabs`, `Dialog`, `Drawer`, `ProgressRing`, `NumberCountUp`).
- **Floating Capsule Navbar**: Center-aligned capsule navigation bar with active-tab layout animations and mobile responsiveness.

---

## [Phase 6] - 2026-11-04
### Added
- **Executive Report Exporters**: Headless PDF generator using ReportLab and Matplotlib, and GitHub-Flavored Markdown exporter.
- **Distributed Tracing & Observability**: SQLite trace logging and Prometheus metrics endpoint (`GET /metrics`).
- **Golden Evaluation Benchmark**: 32-question automated evaluation harness (`eval/run_eval.py`) with 100% execution accuracy scorecard.

---

## [Phase 5] - 2026-11-04
### Added
- **Advanced Specialist Tools**: Multivariate anomaly detection (`AnomalyTool` using IQR, Z-score, Isolation Forest), Holt-Winters time-series forecasting (`ForecastTool`), and root-cause hypothesis testing (`HypothesisTool`).
- **Skeptic Verifier**: Automated verifier performing independent cross-engine calculations (SQL vs. Pandas) and redacting ungrounded numerical claims.
- **Verified Semantic Cache**: SHA-256 schema-aware cache for high-confidence verified answers.

---

## [Phase 4] - 2026-11-04
### Added
- **Plan-Execute-Verify-Narrate (PEVN) Engine**: Core agent engine with 8-lane intent routing and cycle-free DAG planning (Kahn's algorithm).
- **Concurrent Execution**: Parallel wave scheduling using Python `asyncio.gather`.
- **Real-Time SSE Streaming**: Event stream broadcasting route, plan, step lifecycle, verify, tokens, charts, and final narrative.

---

## [Phase 3] - 2026-11-04
### Added
- **Unified LLM Provider Layer**: Raw REST adapters for Groq, Gemini, OpenRouter, and OpenAI-compatible endpoints with token and cost tracking.
- **Safety Guardrails**: Strict SELECT-only AST validation via `sqlglot`, isolated Pandas sandbox, and prompt injection defense.

---

## [Phase 2] - 2026-11-04
### Added
- **Data Ingestion Pipeline**: Delimiter sniffing, encoding detection, DuckDB table staging, and schema validation.
- **Data Quality Auditor**: 0–100 data health score measuring missing values, duplicate rows, impossible values, and outliers.
- **Relationship Detector**: Cross-table join discovery via column name similarity and value overlap analysis.
- **Semantic Catalog**: Heuristic and LLM column descriptions and TF-IDF semantic search.

---

## [Phase 1] - 2026-11-04
### Added
- **Monorepo Foundation**: FastAPI backend app factory, Vite + React 18 + TypeScript frontend, Makefile, Docker Compose, and GitHub Actions CI.
- **Deterministic Mock Provider**: Offline rule-based provider enabling 100% hermetic testing with zero API keys required.
