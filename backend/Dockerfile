# Multi-stage Dockerfile for Lumen Backend
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd -g 1001 lumen && \
    useradd -u 1001 -g lumen -m -s /bin/bash lumen

# Copy installed packages from builder
COPY --from=builder /root/.local /home/lumen/.local

ENV PATH=/home/lumen/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY backend/app ./app
COPY backend/pyproject.toml .

RUN mkdir -p /app/data && chown -R lumen:lumen /app

USER lumen

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
