# Lumen API Documentation

All endpoints are versioned under `/api/v1` (with `/health` and `/ready` also exposed at root).

## Endpoints

### Health & Observability
- `GET /health`: Basic health check.
- `GET /ready`: Storage and service readiness check.
- `GET /api/v1/providers/status`: LLM provider connectivity status.
- `GET /metrics`: Prometheus metrics scrape endpoint.

### Authentication
- `POST /api/v1/auth/register`: Register user account.
- `POST /api/v1/auth/login`: Authenticate and issue JWT tokens.
- `GET /api/v1/auth/me`: Current user profile.

### Datasets
- `POST /api/v1/upload`: Multi-file CSV upload.
- `GET /api/v1/datasets`: List user datasets.
- `GET /api/v1/datasets/{id}`: Detailed profile, quality, and catalog.
- `DELETE /api/v1/datasets/{id}`: Delete dataset.

### Chat & Evidence
- `POST /api/v1/chat/sessions`: Create chat session.
- `POST /api/v1/chat/sessions/{id}/messages`: Query endpoint streaming SSE events.
- `GET /api/v1/chat/messages/{id}/evidence`: Inspect Evidence Ledger.

### Dashboards & Reports
- `POST /api/v1/dashboards/generate`: Generate 4-6 widgets.
- `POST /api/v1/reports/export`: Export session as PDF or Markdown.
- `GET /api/v1/reports/download/{filename}`: Download generated report.
