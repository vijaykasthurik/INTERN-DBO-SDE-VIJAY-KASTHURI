# Requirements audit

Source evidence: `docs/NEEDS_CHECKLIST.md`, `docs/media/final-audit/observations.json`, `frontend/audit-final.cjs`. FAIL includes incomplete or unverified requirements.

| Requirement | Status | Evidence / root cause |
|---|---|---|
| R1 | FAIL | N1: App.tsx mounts app Navbar globally, app routes lack ProtectedRoute; public routes render 404. |
| R2 | FAIL | N2: LandingPage.tsx includes steps, but demo uses fixed sample revenue and claims exceed verified behavior. |
| R3 | FAIL | N1: App.tsx mounts app Navbar globally, app routes lack ProtectedRoute; public routes render 404. |
| R4 | FAIL | N3: /about renders NotFoundPage. |
| R5 | FAIL | N4: /contact is 404; no contact endpoint/model. |
| R6 | FAIL | N5: Navbar uses Sparkles symbol; README has emoji headings; no custom wordmark in PDF. |
| R7 | FAIL | N5: Navbar uses Sparkles symbol; README has emoji headings; no custom wordmark in PDF. |
| R8 | FAIL | N6: Screenshots captured at three widths; motion implementation requires per-component reduced-motion review. |
| R9 | FAIL | N6: Screenshots captured at three widths; motion implementation requires per-component reduced-motion review. |
| R10 | FAIL | N7: upload.py/ingestion.py only ingest_csv; DatasetsPage does not auto-redirect. |
| R11 | FAIL | N8: Live SQL scopes and guarded joins exist; reorder is React state only; quality/anomaly modules incomplete. |
| R12 | FAIL | N9: rows endpoint paginates; rename/replace endpoints and search/sort absent; report cascade missing. |
| R13 | FAIL | N12: Authenticated artifacts and preview exist; PDF text extraction and wordmark unverified. |
| R14 | FAIL | N10: planner overview counts exist; live plan lacks full catalog/relationship contract. Prior live eval fails. |
| R15 | FAIL | N15: Provider routing excludes mock for live configuration; dev offline label and per-key status incomplete. |
| R16 | FAIL | N16: Docker executable missing; no XLSX sample; README and traceability contain stale green claims. |
