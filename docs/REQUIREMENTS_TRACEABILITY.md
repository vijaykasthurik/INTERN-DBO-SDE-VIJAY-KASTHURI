# Lumen Requirements Traceability Matrix

This document provides a comprehensive traceability matrix mapping every core requirement, architectural constraint, and bonus capability of **Lumen: AI-Powered Data Analyst** to its implementation files, test coverage, and visual media proof.

---

## 1. Traceability Matrix

| Requirement / Capability | Category | Implementation Files | Automated Tests | Visual Media Proof | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Multi-File CSV Upload & Ingestion** | Core | [`backend/app/api/upload.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/api/upload.py)<br>[`backend/app/data/ingestion.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/data/ingestion.py) | `tests/unit/test_datasets.py`<br>`frontend/e2e/smoke.spec.ts` | [`docs/media/screenshots/datasets_profile.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/datasets_profile.png) | **Verified** |
| **Data Profiling & Health Scoring (0–100)** | Bonus | [`backend/app/data/profiler.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/data/profiler.py)<br>[`backend/app/data/quality.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/data/quality.py) | `tests/unit/test_datasets.py`<br>`tests/integration/test_pipeline.py` | [`docs/media/screenshots/datasets_profile.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/datasets_profile.png) | **Verified** |
| **Semantic Catalog & Join Graph** | Core | [`backend/app/data/catalog.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/data/catalog.py)<br>[`backend/app/data/relationships.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/data/relationships.py) | `tests/unit/test_datasets.py`<br>`tests/integration/test_pipeline.py` | [`docs/media/screenshots/datasets_profile.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/datasets_profile.png) | **Verified** |
| **Natural Language Chat & SSE Streaming** | Core | [`backend/app/api/chat.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/api/chat.py)<br>[`backend/app/agent/narrator.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/agent/narrator.py) | `tests/unit/test_chat.py`<br>`frontend/e2e/workspace.spec.ts` | [`docs/media/screenshots/workspace_active.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_active.png) | **Verified** |
| **PEVN Autonomous Agent Pipeline** | Core | [`backend/app/agent/engine.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/agent/engine.py)<br>[`backend/app/agent/planner.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/agent/planner.py)<br>[`backend/app/agent/executor.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/agent/executor.py) | `tests/unit/test_agent_engine.py`<br>`eval/run_eval.py` (32 tests) | [`docs/media/screenshots/workspace_active.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_active.png) | **Verified** |
| **Evidence Ledger & Zero-Hallucination Grounding** | Core (P1, P2) | [`backend/app/agent/ledger.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/agent/ledger.py)<br>[`backend/app/agent/verifier.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/agent/verifier.py) | `tests/unit/test_ledger.py`<br>`tests/unit/test_verifier.py` | [`docs/media/screenshots/workspace_evidence_drawer.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_evidence_drawer.png) | **Verified** |
| **Autonomous SQL Tool (DuckDB JOIN-aware)** | Core | [`backend/app/tools/sql_tool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/tools/sql_tool.py)<br>[`backend/app/safety/sql_validator.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/safety/sql_validator.py) | `tests/unit/test_tools.py`<br>`scripts/smoke_test.py` | [`docs/media/screenshots/workspace_evidence_drawer.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_evidence_drawer.png) | **Verified** |
| **Sandboxed Pandas Execution** | Core | [`backend/app/tools/pandas_tool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/tools/pandas_tool.py)<br>[`backend/app/safety/pandas_sandbox.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/safety/pandas_sandbox.py) | `tests/unit/test_tools.py` | [`docs/media/screenshots/workspace_evidence_drawer.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_evidence_drawer.png) | **Verified** |
| **Smart Chart Picker (Apache ECharts)** | Core | [`backend/app/tools/chart_tool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/tools/chart_tool.py)<br>[`frontend/src/features/chat/ChartRenderer.tsx`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/frontend/src/features/chat/ChartRenderer.tsx) | `tests/unit/test_tools.py`<br>`frontend/e2e/workspace.spec.ts` | [`docs/media/screenshots/workspace_active.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_active.png) | **Verified** |
| **Statistical Anomaly Detection** | Bonus | [`backend/app/tools/anomaly_tool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/tools/anomaly_tool.py) | `tests/unit/test_tools.py`<br>`eval/run_eval.py` (#17–#18) | [`docs/media/screenshots/workspace_active.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_active.png) | **Verified** |
| **Holt-Winters Time Series Forecasting** | Bonus | [`backend/app/tools/forecast_tool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/tools/forecast_tool.py) | `tests/unit/test_tools.py`<br>`eval/run_eval.py` (#19–#20) | [`docs/media/screenshots/workspace_active.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_active.png) | **Verified** |
| **Hypothesis Testing & Root-Cause Analysis** | Bonus | [`backend/app/tools/hypothesis_tool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/tools/hypothesis_tool.py) | `tests/unit/test_tools.py`<br>`eval/run_eval.py` (#21–#22) | [`docs/media/screenshots/workspace_active.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/workspace_active.png) | **Verified** |
| **Auto-Generated Executive Dashboards** | Bonus | [`backend/app/tools/dashboard_tool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/tools/dashboard_tool.py)<br>[`backend/app/api/dashboards.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/api/dashboards.py) | `tests/unit/test_dashboards.py`<br>`frontend/e2e/dashboards_reports_settings.spec.ts` | [`docs/media/screenshots/dashboards_executive.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/dashboards_executive.png) | **Verified** |
| **Dossier Export (PDF & Markdown)** | Bonus | [`backend/app/reports/pdf.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/reports/pdf.py)<br>[`backend/app/reports/markdown.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/reports/markdown.py) | `tests/unit/test_reports.py`<br>`frontend/e2e/dashboards_reports_settings.spec.ts` | [`docs/media/screenshots/reports_dossier.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/reports_dossier.png) | **Verified** |
| **Bring Your Own Key (BYOK) + Smart Fallback** | Bonus (Addendum) | [`backend/app/llm/catalog.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/llm/catalog.py)<br>[`backend/app/llm/pool.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/llm/pool.py)<br>[`frontend/src/components/ConnectAIPopup.tsx`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/frontend/src/components/ConnectAIPopup.tsx) | `tests/unit/test_byok_security_and_catalog.py`<br>`tests/unit/test_phase11_drills.py`<br>`frontend/e2e/byok.spec.ts` | [`docs/media/screenshots/settings_diagnostics.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/settings_diagnostics.png) | **Verified** |
| **Observability, Tracing & Prometheus** | Core | [`backend/app/observability/tracing.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/observability/tracing.py)<br>[`backend/app/observability/metrics.py`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/backend/app/observability/metrics.py) | `tests/unit/test_tools.py` | [`docs/media/screenshots/settings_diagnostics.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/settings_diagnostics.png) | **Verified** |
| **Responsive Luxury UI & Floating Capsule Nav** | Core | [`frontend/src/components/Navbar.tsx`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/frontend/src/components/Navbar.tsx)<br>[`frontend/src/pages/LandingPage.tsx`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/frontend/src/pages/LandingPage.tsx) | `frontend/e2e/smoke.spec.ts`<br>`frontend/e2e/dashboards_reports_settings.spec.ts` | [`docs/media/screenshots/landing_hero.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/landing_hero.png)<br>[`docs/media/screenshots/landing_mobile_375.png`](file:///c:/Projects%20Vijay/DBO%20INTERN%20TASK/docs/media/screenshots/landing_mobile_375.png) | **Verified** |

---

## 2. Six Mandatory Benchmark Questions Verification

All 6 core business questions are evaluated deterministically against ground truth and verified with Playwright E2E:

1. **"What is the total revenue per month and year-over-year growth?"**
   - **Route**: `analysis` (SQL Tool + Chart Tool)
   - **Verification**: `eval/run_eval.py` Q1–Q3; Playwright `workspace.spec.ts`
   - **Result**: Grouped DuckDB monthly aggregation, line chart, YoY delta verified against Evidence Ledger.
2. **"Which product category has the highest average discount?"**
   - **Route**: `quick_lookup` (SQL Tool)
   - **Verification**: `eval/run_eval.py` Q7; Playwright `workspace.spec.ts`
   - **Result**: `Software` identified at 12.4% avg discount, cross-checked with Pandas.
3. **"Are there any outliers or anomalies in the order amounts?"**
   - **Route**: `anomaly` (Anomaly Tool)
   - **Verification**: `eval/run_eval.py` Q17–Q18; Playwright `workspace.spec.ts`
   - **Result**: 5 giant synthetic outlier orders (`ORD-OUT-01` to `05`) flagged via Z-score > 3.0 and IQR > 1.5.
4. **"Forecast the sales for the next 3 months."**
   - **Route**: `forecast` (Forecast Tool)
   - **Verification**: `eval/run_eval.py` Q19–Q20; Playwright `workspace.spec.ts`
   - **Result**: Holt-Winters additive exponential smoothing with 95% confidence bounds.
5. **"Why did sales drop in March 2024 in EMEA?"**
   - **Route**: `investigation` (Hypothesis Tool)
   - **Verification**: `eval/run_eval.py` Q21–Q22; Playwright `workspace.spec.ts`
   - **Result**: Generates 3 candidate hypotheses, tests order count and avg value, identifies regional drop as top evidence cause.
6. **"Can you build a dashboard summarizing sales performance?"**
   - **Route**: `dashboard` (Dashboard Tool)
   - **Verification**: `tests/unit/test_dashboards.py`; Playwright `dashboards_reports_settings.spec.ts`
   - **Result**: 4 interactive ECharts widgets executed in parallel, persisted, drag-to-reorder enabled.
