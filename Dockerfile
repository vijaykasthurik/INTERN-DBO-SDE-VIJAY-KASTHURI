# syntax=docker/dockerfile:1
# Lumen Production Single-Service Container
# Builds React SPA and packages with FastAPI Python 3.12 runner for Render / Cloud deployment

# =====================================================================
# Stage 1: Frontend Builder (Node 20 Alpine)
# =====================================================================
FROM node:20-alpine AS builder-frontend
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# =====================================================================
# Stage 2: Backend Dependencies Builder (Python 3.12 Slim)
# =====================================================================
FROM python:3.12-slim AS builder-backend
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# =====================================================================
# Stage 3: Production Runtime (Python 3.12 Slim + Non-Root User)
# =====================================================================
FROM python:3.12-slim AS runner
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder-backend /install /usr/local

# Memory optimization & execution environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    WEB_CONCURRENCY=1 \
    PORT=10000 \
    DATA_DIR=/app/data \
    FRONTEND_DIST_DIR=/app/frontend/dist

# Create secure non-root application user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -s /bin/bash -m appuser

# Create directories with appuser ownership
RUN mkdir -p /app/data /app/frontend/dist && \
    chown -R appuser:appuser /app

# Copy Alembic and Backend application code
COPY --chown=appuser:appuser backend/alembic.ini ./
COPY --chown=appuser:appuser backend/alembic/ ./alembic/
COPY --chown=appuser:appuser backend/app/ ./app/

# Copy compiled frontend distribution from Stage 1
COPY --chown=appuser:appuser --from=builder-frontend /app/frontend/dist ./frontend/dist

USER appuser

EXPOSE 10000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
