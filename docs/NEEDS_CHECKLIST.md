# Needs audit — current checkout

Audit: 2026-11-04. Product code unchanged during this stage. `node frontend/audit-final.cjs` captured 48 signed-out/signed-in route/viewport observations in `docs/media/final-audit/observations.json`. Screenshots are audit evidence, not refreshed submission media. Historical test claims are not counted as new PASS evidence.

| Need | Status | Evidence / root cause | Planned fix |
|---|---|---|---|
| N1 Public site and access control | MISSING | App.tsx mounts app Navbar globally, app routes lack ProtectedRoute; public routes render 404. | Add public navigation/routes and wire existing guard. |
| N2 Home usage instructions | PARTIAL | LandingPage.tsx includes steps, but demo uses fixed sample revenue and claims exceed verified behavior. | Preserve layout; make demo explicitly illustrative or use real uploaded evidence; correct unsupported claims. |
| N3 Fair About comparison | MISSING | /about renders NotFoundPage. | Add fair text comparison in existing tokens with when-to-use guidance. |
| N4 Real contact form | MISSING | /contact is 404; no contact endpoint/model. | Add validated/rate-limited/honeypot persistence and optional SMTP. |
| N5 Branding and no emoji/provider logos | PARTIAL | Navbar uses Sparkles symbol; README has emoji headings; no custom wordmark in PDF. | Add shared SVG wordmark; remove emoji and provider imagery. |
| N6 Complete responsive/reduced motion UI | PARTIAL | Screenshots captured at three widths; motion implementation requires per-component reduced-motion review. | Fix observed overflow only; verify motion accessibility and layout shifts. |
| N7 CSV/Excel upload and dashboard redirect | PARTIAL | upload.py/ingestion.py only ingest_csv; DatasetsPage does not auto-redirect. | Add multi-sheet XLSX with validation; redirect only after confirmed success. |
| N8 Live scoped dashboards | PARTIAL | Live SQL scopes and guarded joins exist; reorder is React state only; quality/anomaly modules incomplete. | Persist order; wire refresh/quality/anomalies and dataset-change invalidation. |
| N9 Dataset management | PARTIAL | rows endpoint paginates; rename/replace endpoints and search/sort absent; report cascade missing. | Add persisted rename/replace/search/sort/type metadata and complete cascade. |
| N10 Grounded overview and cross-file agent | PARTIAL | planner overview counts exist; live plan lacks full catalog/relationship contract. Prior live eval fails. | Plan rich live profile evidence and validated relationship joins. |
| N11 Exact-code actions | PARTIAL | SQL Run exists; no editable/download code or Pandas Run; rerun result is only status text. | Add validated editing/download and sandboxed Pandas rerun with result table. |
| N12 Real reports | PARTIAL | Authenticated artifacts and preview exist; PDF text extraction and wordmark unverified. | Add real wordmark and text extraction regression tests. |
| N13 All other controls | PARTIAL | Session rename/delete routes absent; all-controls tests absent; copy assumes clipboard success. | Inventory each visible control and test real effects; implement missing handlers. |
| N14 BYOK lifecycle | PARTIAL | byok.py and ProfilePage implement endpoints; live failure chain not freshly proven. | Verify lifecycle, masked storage, expiry and fallback events with isolated tests. |
| N15 Live provider and offline labels | PARTIAL | Provider routing excludes mock for live configuration; dev offline label and per-key status incomplete. | Expose indexed health, honest offline label, and prove live flow. |
| N16 Docker and clean-clone delivery | PARTIAL | Docker executable missing; no XLSX sample; README and traceability contain stale green claims. | Generate XLSX, refresh docs/media, secret scan/history, clean-clone test; report Docker host prerequisite. |
