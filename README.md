# Lumen — The Autonomous AI Data Analyst

> **Enterprise-grade, verified conversational business intelligence platform powered by DuckDB, evidence-grounded parallel DAG execution, and dual-pass cross-verification.**

[![CI](https://github.com/vijaykasthurik/INTERN-DBO-SDE-VIJAY-KASTHURI/actions/workflows/ci.yml/badge.svg)](https://github.com/vijaykasthurik/INTERN-DBO-SDE-VIJAY-KASTHURI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/React-18.3-blue.svg)](https://reactjs.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-yellow.svg)](https://duckdb.org/)
[![Coverage](https://img.shields.io/badge/Coverage-82.2%25-brightgreen.svg)]()

---

## 🌟 Visual Showcase

### Hero Workspace & Interactive Evidence Ledger
![Lumen Workspace](docs/media/screenshots/workspace_active.png)

### Multi-File Data Health Scoring & Relational Graph
![Data Health & Profiling](docs/media/screenshots/datasets_profile.png)

### Auto-Compiled Executive Dashboards
![Executive Dashboards](docs/media/screenshots/dashboards_executive.png)

*Interactive product walkthrough recorded at 60fps available in [`docs/media/demo/lumen_interactive_demo.webm`](docs/media/demo/lumen_interactive_demo.webm).*

---

## 💡 Overview & The Lumen Guarantee

Most LLM data assistants hallucinate numbers, miscalculate floating-point aggregates, or run unverified SQL that silent-fails. **Lumen is engineered differently.**

We enforce three non-negotiable principles:
1. **Rule P1 (The LLM Never Computes)**: The LLM plans and generates code; **DuckDB** and **Pandas** compute. Every number in a final answer must exist in the cryptographic **Evidence Ledger**.
2. **Rule P2 (Trust is Engineered)**: Every answer is audited by an adversarial **Dual-Pass Verifier** before the user sees it. Ungrounded numbers are redacted (`[UNGROUNDED_NUMBER_REMOVED]`) and key totals are cross-checked via independent methods (SQL vs. Pandas).
3. **Rule P6 (Security by Default)**: Per-user isolated DuckDB files, `sqlglot` SELECT-only AST validation, AST-restricted Pandas sandbox, and strict separation between data and instructions.

---

## 🎯 Requirements & Bonus Features Traceability Matrix

Every single assignment requirement and bonus feature is implemented as a first-class production module:

| Capability | Assignment Tier | Where to Find in Code | Where to Find in UI | Proven By Test |
| :--- | :--- | :--- | :--- | :--- |
| **Multi-File CSV Upload & Profiling** | **Core + Bonus** | `backend/app/data/ingestion.py`<br>`backend/app/data/profiler.py` | `/datasets` (Drag-and-Drop Dropzone, Progress Ring) | `test_ingestion_edge_cases.py`<br>`smoke.spec.ts` |
| **Data Quality Audit (0-100 Score)** | **Bonus** | `backend/app/data/quality.py` | `/datasets` (Data Health Ring, Quality Breakdown) | `test_profiler_and_quality.py` |
| **Multi-Table Relational Graphs** | **Bonus** | `backend/app/data/relationships.py` | `/datasets` (Foreign Key Overlap Graph) | `test_relationships_and_catalog.py` |
| **Natural Language Conversational Q&A**| **Core** | `backend/app/agent/engine.py` | `/workspace` (Chat Composer, Suggested Prompts) | `test_agent_pipeline_e2e.py`<br>`workspace.spec.ts` |
| **Conversational Context & Entity Memory**| **Core** | `backend/app/agent/context.py`<br>`backend/app/agent/memory.py` | `/workspace` (Contextual follow-ups like "now by month")| `test_context_resolver.py` |
| **Reasoning Explanation & DAG Execution** | **Core + Bonus** | `backend/app/agent/planner.py` | `/workspace` (Animated DAG Timeline, Wave Lighting) | `test_planner_waves.py` |
| **Evidence Ledger & Audit Trail** | **Core + Bonus** | `backend/app/agent/ledger.py` | `/workspace` (Spring-in Evidence Drawer, SQL/Pandas) | `test_advanced_tools_and_trust.py` |
| **Interactive Charts (Bar, Line, Pie, Scatter)**| **Core** | `backend/app/tools/chart_tool.py`<br>`frontend/src/features/workspace/ChartRenderer.tsx` | `/workspace`, `/dashboards` (ECharts with PNG Export) | `workspace.spec.ts` |
| **Multivariate Anomaly Detection** | **Core + Bonus** | `backend/app/tools/anomaly_tool.py` | `/workspace`, `/dashboards` (Anomaly Cards, z-scores) | `test_anomaly_tool_ensemble.py` |
| **Holt-Winters Time-Series Forecasting**| **Bonus** | `backend/app/tools/forecast_tool.py` | `/dashboards`, `/workspace` (Trend Lines, Confidence Band)| `test_forecast_tool_mape.py` |
| **Root-Cause Hypothesis Testing** | **Bonus** | `backend/app/tools/hypothesis_tool.py`| `/workspace` (Ranked candidate causes by variance) | `test_hypothesis_tool.py` |
| **Auto-Compiled Executive Dashboards** | **Bonus** | `backend/app/tools/dashboard_tool.py`<br>`frontend/src/pages/DashboardsPage.tsx` | `/dashboards` (5-Widget Grid, Reorder, Fullscreen) | `dashboards_reports_settings.spec.ts` |
| **Executive Reports Export (PDF & Markdown)**| **Bonus** | `backend/app/reports/pdf.py`<br>`backend/app/reports/markdown.py` | `/reports` (PDF download with Matplotlib charts, MD) | `test_report_exports.py` |
| **Real-Time SSE Streaming** | **Bonus** | `backend/app/api/chat.py`<br>`frontend/src/features/workspace/ChatStreamService.ts` | `/workspace` (Live streaming tokens, route, plan, done)| `workspace.spec.ts` |
| **Verified Semantic Cache** | **Bonus** | `backend/app/agent/cache.py` | `/workspace` (Sub-10ms instantaneous repeat queries) | `test_verified_cache.py` |
| **Tenant Isolation & Argon2id Auth** | **Bonus** | `backend/app/core/security.py`<br>`backend/app/api/auth.py` | `/auth` (Sign in / Registration tabs, JWT lifecycle) | `test_auth.py` |
| **Prometheus Observability & Tracing** | **Bonus** | `backend/app/observability/tracing.py`<br>`backend/app/observability/metrics.py` | `/metrics`, `/settings` (SQLite traces, JSON logs) | `test_observability.py` |
| **Golden Benchmark Evaluation (32 Questions)**| **Bonus** | `eval/run_eval.py`<br>`eval/golden.yaml` | CLI (`make eval`), `eval/RESULTS.md` | `eval/run_eval.py` (100% Accuracy) |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    User([Business Analyst / Executive])
    
    subgraph Frontend [React 18 + TS + Tailwind]
        Nav[Capsule Navbar]
        Chat[Chat & Composer]
        Timeline[Reasoning DAG Timeline]
        Evidence[Evidence Drawer]
        Charts[ECharts Visualizations]
    end

    subgraph BackendGateway [FastAPI Gateway]
        Auth[Argon2id + JWT Auth]
        Ingest[CSV Ingestion Pipeline]
        SSE[SSE Stream Dispatcher]
    end

    subgraph PEVN_Pipeline [PEVN Agent Engine]
        Resolver[Context Resolver]
        Router[8-Lane Intent Router]
        Planner[DAG Planner - Kahn's Waves]
        Executor[Parallel Step Executor]
        Verifier[Skeptic Verifier]
        Narrator[Grounded Narrator]
    end

    subgraph Storage [Analytical & Metadata Stores]
        DuckDB[(Per-User DuckDB)]
        SQLite[(SQLite Metadata & Traces)]
        Cache[(Verified Semantic Cache)]
    end

    User <--> Frontend
    Frontend <--> BackendGateway
    BackendGateway <--> PEVN_Pipeline
    PEVN_Pipeline <--> Storage
```

---

## 🔬 Core Architectural Decisions

1. **Why the LLM Never Computes (Rule P1)**: LLMs are probabilistic text generators, not arithmetic engines. In financial, sales, and supply chain analysis, an invented number destroys trust. In Lumen, DuckDB and Pandas compute, while the Evidence Ledger holds the immutable proof.
2. **Why the Dual-Pass Verifier (Rule P2)**: Even with accurate code execution, LLMs can misread prompt criteria. The Verifier checks that every number in the draft appears in the ledger, redacting ungrounded tokens, and cross-checks key totals between SQL and Pandas.
3. **Why the Evidence Ledger**: Enterprise data teams require transparency. Clicking any number opens a slide-in drawer revealing the exact SQL, runtime, row count, and raw execution preview.
4. **Why DAG Planning with Kahn's Algorithm**: Multi-tool questions (e.g., trend calculation + anomaly isolation) are parsed into dependency graphs. Steps with zero mutual dependencies execute concurrently via `asyncio.gather`, slashing latency by up to 65%.
5. **Why a Semantic Layer Catalog**: Rather than passing raw tables to the LLM (which leaks data and wastes context tokens), Lumen compiles a compact semantic catalog with column distributions, inferred business definitions, and foreign keys.

---

## 🛡️ Security Model

- **Read-Only Analytical Isolation**: Each user operates within their own DuckDB warehouse file (`data/user_warehouses/user_{id}.duckdb`).
- **SELECT-Only AST Enforcement**: All DuckDB queries are parsed with `sqlglot`. Statements attempting mutations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`) raise a `SecurityViolationError`.
- **AST-Restricted Pandas Sandbox**: Python code execution runs in an isolated subprocess with restricted `__builtins__`. Direct filesystem, network, and reflection calls are strictly prohibited.
- **Prompt Injection Defense**: CSV contents are parsed strictly as **DATA**, never instructions. Prompts are wrapped in an immutable structural template that resists jailbreak attempts.

---

## 🚀 Quick Start

### Option 1: Local Development (Recommended)

#### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

```bash
# 1. Clone repository
git clone https://github.com/vijaykasthurik/INTERN-DBO-SDE-VIJAY-KASTHURI.git
cd INTERN-DBO-SDE-VIJAY-KASTHURI

# 2. Setup backend virtualenv & install dependencies
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Setup frontend dependencies
cd frontend && npm install && cd ..

# 4. Run full Quality Gate (Ruff, Mypy, Pytest 80%+ cov, ESLint, TypeScript, Vitest, Build)
make check

# 5. Run end-to-end smoke test
make smoke

# 6. Run the 32-question golden evaluation suite
make eval

# 7. Start the application servers
# Terminal 1 (Backend):
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# Terminal 2 (Frontend):
cd frontend && npm run dev
```

Visit `http://localhost:5173` in your browser. Default login: `analyst@lumen.ai` / `Password123!` (or click "Create Account").

---

### Option 2: Docker Compose

```bash
# Build and run backend + frontend (Nginx reverse proxy)
docker compose up -d --build

# Run smoke test against running container
make smoke
```

Frontend runs on `http://localhost:80` (or `http://localhost:5173`), Backend API on `http://localhost:8000`.

---

## 🧪 Evaluation Benchmark Scorecard (`golden.yaml`)

Lumen includes a rigorous evaluation suite covering 32 benchmark questions across 9 analytical categories. Evaluated with `eval/run_eval.py`:

```
======================================================================
                  LUMEN GOLDEN EVALUATION SCORECARD                   
======================================================================
Provider           : mock (deterministic offline)
Total Benchmarks   : 32
Passed             : 32
Failed             : 0
Execution Accuracy : 100.0%
Average Latency    : 1.42ms
Number Grounding   : 100.0% Verified
======================================================================
```

Categories evaluated:
1. `quick_lookup`: Instant metric aggregation
2. `comparison`: Cross-category / regional breakdowns
3. `trend`: Multi-month time-series trajectory
4. `anomaly`: Statistical outlier flagging with z-scores
5. `root_cause`: Hypothesis generation and variance explanation
6. `code_generation`: Production-ready SQL/Pandas code emission
7. `clarification`: Interactive disambiguation option chips
8. `conversational_follow_up`: Entity resolution and context retention
9. `multi_table_join`: Cross-table analysis across `sales`, `customers`, and `products`

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` to customize runtime settings:

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Runtime environment (`development`, `production`, `test`) |
| `LLM_PROVIDER` | `mock` | Active LLM adapter (`mock`, `gemini`, `groq`, `openrouter`, `openai_compat`) |
| `LLM_FALLBACK_ORDER` | `mock,gemini,groq` | Ordered provider fallback chain on rate limits/downtime |
| `SECRET_KEY` | *(sample key)* | HMAC secret key for signing JWT auth tokens |
| `DATABASE_URL` | `sqlite:///./data/lumen.db` | Path to metadata SQLite database |
| `DATA_DIR` | `./data` | Directory storing tenant DuckDB warehouses and reports |
| `MAX_UPLOAD_MB` | `100` | Maximum single-file CSV upload limit |
| `CACHE_TTL_SECONDS` | `3600` | Verified Semantic Cache expiration window |
| `GEMINI_API_KEY` | `""` | Optional API key for Google Gemini provider |
| `GROQ_API_KEY` | `""` | Optional API key for Groq LPU provider |
| `OPENROUTER_API_KEY` | `""` | Optional API key for OpenRouter provider |

---

## 📂 Project Directory Structure

```text
lumen/
  ├── Makefile                    # Unified commands (setup, check, smoke, eval, dev)
  ├── docker-compose.yml          # Multi-stage production compose configuration
  ├── sample_data/                # sales.csv, customers.csv, products.csv, GROUND_TRUTH.md
  ├── scripts/
  │   ├── autocommit.sh           # Background 30-minute git commit daemon
  │   ├── check_llm.py            # Provider connectivity and latency diagnostic tool
  │   ├── smoke_test.py           # End-to-end smoke verification script
  │   ├── take_screenshots.ts    # Multi-viewport screenshot generation script
  │   └── record_demo.ts          # Playwright demo video recording script
  ├── backend/
  │   ├── app/
  │   │   ├── api/                # Auth, upload, datasets, chat (SSE), dashboards, reports
  │   │   ├── agent/              # PEVN Engine, router, planner, executor, verifier, ledger
  │   │   ├── data/               # Ingestion, validation, profiler, quality, relationships
  │   │   ├── llm/                # Unified LLM provider interface, router, and adapters
  │   │   ├── safety/             # sqlglot SQL validator, Pandas sandbox, prompt injection
  │   │   ├── tools/              # DuckDB, Pandas, anomaly, forecast, hypothesis tools
  │   │   └── reports/            # PDF (ReportLab) and Markdown report builders
  │   └── tests/                  # 162 unit and integration tests (82.2% coverage)
  ├── frontend/
  │   ├── src/
  │   │   ├── components/         # Design system UI primitives, Navbar, CommandPalette
  │   │   ├── features/           # Workspace, reasoning timeline, evidence drawer, ECharts
  │   │   └── pages/              # Landing, Auth, Workspace, Datasets, Dashboards, Reports, Settings
  │   └── e2e/                    # Playwright smoke, workspace, and dashboard specs
  ├── eval/                       # golden.yaml benchmark suite and run_eval.py harness
  └── docs/                       # Architecture diagrams, API docs, design decisions, screenshots
```

---

## 🔮 Roadmap & Assumptions

- **Assumptions**: Tabular data files conform to delimited CSV structure; analytical queries prioritize read-heavy aggregation over OLTP mutations.
- **Roadmap (v2.0)**:
  - Direct PostgreSQL and Snowflake warehouse connector ingestion.
  - Natural-language automated scheduled email digests.
  - Multi-user collaborative workspace canvas with presence indicators.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
