# Lumen API Reference (v1)

Base URL: `http://localhost:8000/api/v1`  
All responses follow consistent JSON formats. Authenticated routes require an `Authorization: Bearer <token>` header.

---

## 1. Authentication (`/auth`)

### `POST /auth/register`
Create a new user account with Argon2id password hashing.
- **Request Body**:
  ```json
  {
    "email": "analyst@lumen.ai",
    "password": "Password123!"
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "id": 1,
    "email": "analyst@lumen.ai",
    "is_active": true,
    "created_at": "2026-11-04T12:00:00Z"
  }
  ```

### `POST /auth/login`
Authenticate credentials and issue JWT access and refresh token pair.
- **Request Body**:
  ```json
  {
    "email": "analyst@lumen.ai",
    "password": "Password123!"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### `GET /auth/me`
Retrieve current authenticated user profile.
- **Response `200 OK`**: User profile object.

### `POST /auth/clear-data`
Permanently delete all datasets, DuckDB tables, and chat sessions for the authenticated user.
- **Response `200 OK`**:
  ```json
  {
    "message": "All user data, datasets, and chat sessions have been permanently cleared."
  }
  ```

---

## 2. Ingestion & Datasets (`/upload`, `/datasets`)

### `POST /upload`
Upload one or multiple CSV files (up to 100MB per file). Auto-detects delimiters, encodings, and sanitizes identifiers.
- **Content-Type**: `multipart/form-data`
- **Response `201 Created`**:
  ```json
  {
    "total_files": 1,
    "datasets": [
      {
        "id": 1,
        "name": "sales.csv",
        "table_name": "sales",
        "row_count": 4959,
        "column_count": 8,
        "quality_score": 93.9,
        "quality_summary": {
          "duplicate_rows": 0,
          "null_counts": {},
          "impossible_values": []
        }
      }
    ]
  }
  ```

### `GET /datasets`
List all datasets registered to the user's workspace.

### `GET /datasets/{id}`
Retrieve column schema profiles, statistical distributions (min, max, mean, top values), and semantic descriptions.

### `GET /datasets/relationships`
Compute and return the multi-table relational graph with foreign-key overlap scores.

### `PATCH /datasets/{id}/metrics`
Register or update a business metric definition injected into the catalog.
- **Request Body**:
  ```json
  {
    "name": "net_revenue",
    "expression": "SUM(quantity * unit_price * (1.0 - discount))",
    "description": "Net realized sales volume"
  }
  ```

### `DELETE /datasets/{id}`
Remove dataset metadata and drop table from user's DuckDB warehouse.

---

## 3. Conversational Analytics (`/chat`)

### `POST /chat/sessions`
Create a new conversational workspace session.
- **Request Body**: `{"title": "Q1 Performance Analysis"}`
- **Response `201 Created`**: `{"id": "ses_abc123", "title": "...", "created_at": "..."}`

### `GET /chat/sessions`
List all historical sessions.

### `GET /chat/sessions/{id}`
Retrieve entire session conversation history with message confidence and evidence flags.

### `POST /chat/sessions/{id}/messages` (SSE Streaming)
Submit a natural-language inquiry. Streams real-time lifecycle events via Server-Sent Events (SSE).
- **Request Body**:
  ```json
  {
    "content": "Which region generated the highest revenue?"
  }
  ```
- **Stream Event Types**:
  - `event: route`: Intent classification lane (`quick_lookup`, `analysis`, `anomaly`, etc.)
  - `event: plan`: DAG step graph with dependencies
  - `event: step_start`: Execution notification for step `k`
  - `event: step_result`: Runtime and row count for step `k`
  - `event: repair`: Targeted repair notification on query error
  - `event: verify`: Skeptic verifier checklist and High/Medium/Low confidence
  - `event: token`: Streaming narrative text token
  - `event: chart`: Neutral ECharts specification
  - `event: final`: Complete verified markdown answer with follow-up suggestions
  - `event: done`: Stream completion

### `GET /chat/messages/{id}/evidence`
Retrieve the immutable Evidence Ledger entries proving every computation cited in message `{id}`.

---

## 4. Dashboards & Reports (`/dashboards`, `/reports`)

### `POST /dashboards/generate`
Auto-compile 4-6 responsive KPI cards, trend lines, market share charts, and anomaly panels.
- **Response `201 Created`**: Complete dashboard specification with layout and widget data.

### `POST /reports/export`
Generate an executive dossier in PDF or Markdown from Evidence Ledger session history.
- **Request Body**:
  ```json
  {
    "session_id": "ses_abc123",
    "title": "Executive Revenue Brief",
    "format": "pdf"
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "report_id": "rep_9f81a7b0",
    "format": "pdf",
    "download_url": "/api/v1/reports/download/rep_9f81a7b0.pdf",
    "title": "Executive Revenue Brief"
  }
  ```

### `GET /reports/download/{filename}`
Download compiled PDF or Markdown document with appropriate media type headers.

---

## 5. System Health & Observability (`/health`, `/admin`, `/metrics`)

- `GET /health`: Basic health check (`{"status": "ok", "version": "1.0.0"}`)
- `GET /ready`: Readiness check (`{"ready": true, "database": "connected", "storage": "writable"}`)
- `GET /api/v1/providers/status`: LLM router health, circuit breaker state, and latency metrics across all providers.
- `GET /metrics`: Standard Prometheus metrics export.
