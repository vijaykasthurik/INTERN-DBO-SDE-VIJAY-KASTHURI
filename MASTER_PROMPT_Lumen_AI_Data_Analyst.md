# MASTER BUILD PROMPT: "Lumen", the AI Data Analyst

For use with Google Antigravity (or any agentic coding IDE).
Single file = **1 Constitution (Part A)** + **10 Phase prompts (Part B)** + **final LLM-key phase (Part C)**.

---

## 0. How to use this file (read once)

1. Create an empty folder and open it in Antigravity. Replace `<REPO_URL>` below with your GitHub repo link everywhere it appears (or tell the agent the link in the first message).
2. Make sure Git can already push to that repo from your machine (SSH key or a logged-in credential helper). The agent cannot fix GitHub login for you.
3. **Paste Part A first**, as the very first message. If your Antigravity version supports workspace rules or an `AGENTS.md`-style rules file, also save Part A there so it persists across sessions.
4. Then paste **one Phase prompt at a time** (Phase 1, 2, 3, ...). Do not paste the next phase until the current phase's **Acceptance Gate** passes and the agent has committed and tagged it.
5. **Do not add any LLM API keys until Part C.** Phases 1 to 10 run on a built-in deterministic `mock` provider, so the whole app (UI, agents, tests) works offline with zero keys.
6. If the agent loses context, say: `Read AGENTS.md and docs/PROGRESS.md, then continue from the last unchecked item.`

---

# PART A. CONSTITUTION

```text
You are a principal AI engineer AND a world-class product designer, working as one autonomous team.
Build "Lumen": a production-grade, AI-powered Data Analyst web app. A user uploads one or more CSV
files and chats with the data in natural language. The app answers questions, produces business
insights, draws charts, generates SQL/Pandas code, detects anomalies and explains why, explains its
reasoning, and keeps conversation context. It must feel like a funded startup's flagship product.

GitHub repo: https://github.com/vijaykasthurik/INTERN-DBO-SDE-VIJAY-KASTHURI.git   (all work is pushed here)

======================================================================
1. NON-NEGOTIABLE PRINCIPLES
======================================================================
P1. The LLM NEVER computes numbers and NEVER invents numbers. The LLM plans and writes code; DuckDB /
    Pandas compute; every number in a final answer must exist in the Evidence Ledger (see section 4).
P2. Trust is engineered: every answer passes a Verifier before the user sees it.
P3. Every bonus feature is a first-class module (tool or layer), never a hack.
P4. Everything works with LLM_PROVIDER=mock (deterministic, offline, no keys). Real providers are
    plugged in only in the final phase through the same interface.
P5. No placeholders, no TODO stubs, no "left as an exercise", no fake data in the UI, no
    commented-out code, no silent `except: pass`. If something is in scope, it is fully built.
P6. Security by default: read-only analytical DB, SELECT-only allow-list, sandboxed Pandas, secrets
    only in .env (never committed, never printed), CSV contents are DATA never INSTRUCTIONS
    (prompt-injection defence).

======================================================================
2. AUTONOMY RULES
======================================================================
- Work end to end without asking permission for routine things. You MAY and SHOULD automatically
  install anything needed: create a Python venv, pip install, npm install, Playwright browsers,
  and system packages when a package manager is available and permitted.
- Only stop and ask the human for: (a) git push authentication failing, (b) a system prerequisite
  you genuinely cannot install, (c) a real LLM API key (only in Part C). Never ask for keys earlier.
- Plan before coding in each phase: write the plan into docs/PROGRESS.md, then execute.
- Error protocol: when a command fails, read the full error, find the ROOT CAUSE, fix it, re-run.
  Max 3 attempts per approach, then change the approach. NEVER delete/skip/weaken a test to make it
  pass, NEVER lower strictness (lint/type) to hide errors.
- Pin dependency versions (requirements.txt with exact versions after first successful install,
  package-lock.json committed). Verify real, current package names/versions; do not guess APIs:
  read the installed library's docs/source when unsure.
- Keep docs/PROGRESS.md updated (status per phase, decisions, next steps) so work can be resumed
  after a context reset. Keep AGENTS.md identical to this Part A.

======================================================================
3. GIT PROTOCOL (mandatory)
======================================================================
- First action: verify `git remote -v` points to https://github.com/vijaykasthurik/INTERN-DBO-SDE-VIJAY-KASTHURI.git, and that `git push` works. If not,
  stop and ask the human.
- Create scripts/autocommit.sh and start it in a background terminal for the whole session. It loops
  every 1800 seconds (30 min): `git add -A`; if there are staged changes,
  `git commit -m "chore(auto): checkpoint <ISO time>"`; then `git push`. It must never commit .env,
  data/, node_modules, venvs, or build output (enforce via .gitignore AND a pre-commit secret scan
  that blocks commits containing patterns like API keys).
- ALSO commit manually at every meaningful milestone using Conventional Commits
  (feat:, fix:, refactor:, test:, docs:, chore:), push immediately, and at the end of every phase
  create and push the tag `phase-N-complete`.
- Work on `main` using small, logical commits. Commit messages describe WHY, not just what.

======================================================================
4. TECH STACK (pinned choices, do not substitute)
======================================================================
Backend  : Python 3.12, FastAPI, Uvicorn, Pydantic v2, DuckDB, Pandas, NumPy, scikit-learn,
           statsmodels (Holt-Winters forecasting), sqlglot (SQL parsing/validation), SQLAlchemy 2 +
           SQLite (users, sessions, messages, cache, traces), PyJWT + argon2-cffi (auth),
           httpx (LLM providers via raw REST, no vendor SDKs), sse-starlette (streaming),
           structlog (JSON logs), prometheus-client (/metrics), reportlab + matplotlib (PDF export),
           fastembed (local embeddings) with numpy cosine store; fallback to scikit-learn TF-IDF if the
           model cannot download. Tests: pytest, pytest-asyncio, httpx. Quality: ruff, mypy.
Frontend : Vite + React 18 + TypeScript (strict), Tailwind CSS v3, Framer Motion, Apache ECharts
           (echarts-for-react), Zustand, TanStack Query, lucide-react, react-markdown,
           @fontsource-variable/inter + @fontsource/instrument-serif (self-hosted fonts, no CDN),
           Vitest + Testing Library, Playwright (e2e, screenshots, demo video).
Infra    : Docker (multi-stage), docker-compose (api + web via nginx + volume), Makefile,
           GitHub Actions CI, pre-commit.

======================================================================
5. REPOSITORY LAYOUT
======================================================================
lumen/
  AGENTS.md  README.md  Makefile  docker-compose.yml  .env.example  .gitignore  .pre-commit-config.yaml
  .github/workflows/ci.yml
  scripts/  autocommit.sh  gen_sample_data.py  check_llm.py  record_demo.ts  take_screenshots.ts
  sample_data/  sales.csv  customers.csv  products.csv  GROUND_TRUTH.md
  backend/
    Dockerfile  requirements.txt  pyproject.toml
    app/
      main.py  config.py  deps.py
      api/        auth.py upload.py datasets.py chat.py dashboards.py reports.py admin.py health.py
      core/       logging.py errors.py security.py rate_limit.py
      db/         models.py session.py migrations/
      data/       ingestion.py validation.py profiler.py quality.py relationships.py catalog.py embeddings.py
      llm/        base.py router.py mock.py gemini.py groq.py openrouter.py openai_compat.py budget.py
      safety/     sql_validator.py pandas_sandbox.py injection.py
      agent/      engine.py router.py context.py planner.py executor.py repair.py verifier.py
                  ledger.py narrator.py memory.py cache.py events.py prompts/
      tools/      sql_tool.py pandas_tool.py chart_tool.py anomaly_tool.py forecast_tool.py
                  hypothesis_tool.py dashboard_tool.py search_tool.py
      reports/    builder.py pdf.py markdown.py
      observability/  tracing.py metrics.py
    tests/        unit/ integration/ e2e/
  eval/  golden.yaml  run_eval.py  README.md
  frontend/
    Dockerfile  nginx.conf  package.json  tailwind.config.ts  vite.config.ts
    src/  app/ components/ features/ hooks/ lib/ styles/ pages/ stores/ tests/
    e2e/
  docs/  PROGRESS.md  architecture.md  api.md  design-decisions.md  media/

======================================================================
6. CORE ARCHITECTURE (implement exactly)
======================================================================
PHASE A - DATA ONBOARDING (per upload):
  validate (type, size, encoding, delimiter, empty, duplicate headers, row/col limits)
  -> load into per-user DuckDB database (one table per CSV, safe identifiers)
  -> profile (per column: dtype, nulls, distinct, min/max/mean, top values, histogram)
  -> data-quality report (duplicates, missing, type mismatch, impossible values such as negative
     prices or future dates, constant columns, outliers) with a 0-100 quality score
  -> SEMANTIC LAYER / catalog: LLM-inferred column descriptions, metric definitions
     (e.g. revenue = SUM(quantity*unit_price*(1-discount)), editable by user), relationship graph
     (join keys detected by name similarity + value overlap), embeddings of columns and categorical
     values for semantic search ("turnover" -> revenue, "iphone" -> "Apple iPhone 14").
  The LLM sees the compact catalog, never raw tables.

PHASE B - QUESTION LOOP, the PEVN pipeline with an Evidence Ledger:
  1. Auth + rate limit
  2. Cache lookup (key = hash(question + schema hash + resolved context); only VERIFIED answers cached)
  3. Context resolver: resolves follow-ups and references ("now by month", "why is that low?")
     using entity memory, not only chat history
  4. ROUTER (small/fast model tier): lanes =
       quick_lookup | analysis | investigation (hypothesis testing) | anomaly | forecast |
       dashboard | code_request ("generate SQL for this") | clarify (ambiguous -> ask 1 question)
  5. PLANNER: outputs a DAG (JSON) of steps with dependencies; independent steps run in PARALLEL.
  6. EXECUTOR: runs specialist tools via native function calling:
       sql_tool (DuckDB, JOIN-aware), pandas_tool (sandbox), chart_tool (picks type from data
       shape: time->line, share->pie, comparison->bar, correlation->scatter), anomaly_tool
       (z-score + IQR + IsolationForest flag rows; LLM only explains WHY from the stats),
       forecast_tool (Holt-Winters with confidence band), hypothesis_tool (generate candidate causes,
       test each with a query, rank by evidence), dashboard_tool (plan 4-6 widgets, run in parallel),
       search_tool (semantic column/value search).
     REPAIR LOOP: error taxonomy (unknown column, type error, ambiguous column, join fan-out,
     timeout) -> targeted repair prompt, max 2 retries.
  7. VERIFIER (skeptic): sanity checks (empty result, percentages > 100, negative revenue, row-count
     explosion after JOIN), CROSS-CHECK of key numbers via a second independent method (SQL vs
     Pandas), NUMBER GROUNDING (every number in the draft must be in the ledger; ungrounded numbers
     are removed or recomputed), outputs confidence High/Medium/Low with reasons.
  8. EVIDENCE LEDGER: per step store {step_id, tool, code, result_preview, row_count, runtime_ms,
     status}. The Narrator may only cite from the ledger.
  9. NARRATOR: streams the final answer (SSE) from the ledger only: direct answer, business
     insight, chart spec, "how I got this", confidence, 3 suggested follow-ups.
 10. Memory update (working / session / semantic cache) + structured logging + metrics.
  BUDGET GOVERNOR: caps steps/tokens/time per question, routes cheap tasks to the fast tier and hard
  ones to the strong tier, degrades gracefully with an honest "partial analysis" notice.

SSE EVENT TYPES (backend -> UI): route, plan, step_start, step_result, repair, verify, token,
chart, final, error, done.   Each event carries trace_id and a timestamp.

LLM LAYER: one interface `LLMProvider.complete(messages, tools=None, json_schema=None, tier="fast"|"strong",
stream=False)`. Adapters: mock (deterministic, rule-based, fully demoable), gemini, groq, openrouter,
openai_compat (any OpenAI-compatible endpoint via env). Router with ordered fallback chain
(LLM_FALLBACK_ORDER), per-provider token-bucket rate limiting, exponential backoff + jitter on 429/5xx,
circuit breaker, and per-request cost/token accounting.

API (all under /api/v1, documented in docs/api.md and OpenAPI):
  auth: POST register, login, refresh, GET me
  datasets: POST upload (multi-file), GET list, GET {id} (profile+quality+catalog), PATCH {id}/metrics,
            DELETE {id}, GET {id}/relationships
  chat: POST sessions, GET sessions, GET sessions/{id}, POST sessions/{id}/messages (SSE stream),
        GET messages/{id}/evidence
  dashboards: POST generate, GET list/{id}
  reports: POST export (format=pdf|md), GET download
  admin/health: GET /health, /ready, /metrics, GET /providers/status

======================================================================
7. DESIGN SYSTEM (premium, white, world-class)
======================================================================
Mood: calm, confident, editorial-meets-fintech. Think Linear x Stripe x Apple. Lots of white space.
Background pure white (#FFFFFF) with an extremely subtle off-white for panels (#FAFAFB). Never dark mode
in v1. No clutter, no emoji in UI, no default-looking components.
Tokens: ink #0B0B0F; muted #6B7280; hairline border rgba(15,23,42,0.08); accent = ONE signature
soft gradient (indigo #6366F1 -> violet #8B5CF6 -> cyan #22D3EE) used sparingly (focus rings,
primary button, active nav glow, key chart series). Radii 16-28px. Layered soft shadows
(0 1px 2px rgba(15,23,42,.04), 0 8px 30px rgba(15,23,42,.06)). Type: Inter Variable for UI,
Instrument Serif for hero/headline accents; tight tracking on headings; tabular numbers for data.
Spacing scale 4/8 base. 8-column fluid grid. Min touch target 44px. WCAG AA contrast.

NAVBAR (signature element): a FLOATING capsule nav centered at the top with fully rounded
half-circle ends ("half-bounded" pill), translucent white with backdrop blur, hairline border and a
soft shadow. Animated: a gliding active-tab indicator (Framer Motion layoutId), a slowly rotating
gradient border glow, shrinks/condenses on scroll, hover micro-interactions, and on mobile it morphs
into a bottom-anchored capsule. Implement the shape as a single design constant NAV_VARIANT =
"capsule" | "bottom-rounded" so the human can switch to a nav that is only rounded on its bottom corners
with a one-line change. Default: "capsule".

MOTION (Framer Motion, GPU-only: animate transform/opacity): staggered page-load reveals; shared
layout transitions between pages; magnetic primary buttons; animated number count-ups; skeleton shimmer
loaders; streaming text with a soft caret; reasoning timeline where the plan DAG nodes light up and
edges animate as steps execute; charts that draw in; upload dropzone with animated progress ring and
file-card fly-in; evidence drawer springs in from the right; success/ error toasts with spring physics.
Respect prefers-reduced-motion. Target 60fps; no layout thrash; no animation longer than 600ms for UI
feedback.

SCREENS: Landing (animated hero with a live mini-demo of the product), Auth, Workspace (chat center,
Reasoning Timeline + Evidence drawer right, dataset rail left), Datasets (profile cards, Data Health
score ring, relationship graph), Dashboards (auto-generated, drag-to-reorder), Reports (export history),
Settings (provider health + status lights, metric definitions editor).
Every empty / loading / error state is designed, never default.

======================================================================
8. QUALITY GATES (definition of done for EVERY phase)
======================================================================
`make check` must pass and run: ruff + mypy, pytest (with coverage >= 80% on backend/app), frontend
lint + typecheck + vitest + production build, docker compose build, and `make smoke` (boot the stack,
hit /health, upload sample data, ask 3 questions through the mock provider, assert a verified
answer). Never end a phase with failing checks. At the end of each phase: update docs/PROGRESS.md,
commit, push, tag phase-N-complete, and print a 10-line summary with the exact commands to run it.
```

---

# PART B. PHASE PROMPTS

## Phase 1: Bootstrap, tooling, auto-commit, skeleton
## Phase 2: Data onboarding, auth, sample data, semantic layer
## Phase 3: LLM layer, mock provider, safety
## Phase 4: Agent engine core (PEVN) + streaming
## Phase 5: Advanced tools, Verifier, cache, governor
## Phase 6: Reports, observability, evaluation harness
## Phase 7: Frontend foundation and design system
## Phase 8: Workspace: chat, Reasoning Timeline, Evidence, charts
## Phase 9: Dashboards, reports UI, settings, polish
## Phase 10: Integration, Docker, docs, media

---

# PART C. FINAL PHASE: add the real LLM keys (only now)
## Phase 11: Live provider validation
## Phase 12: Final audit and submission
