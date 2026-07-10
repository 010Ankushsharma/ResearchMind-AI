# ──────────────────────────────────────────────────────────────────────────
# Multi-Agent Research & Report Generation Platform — Backend Dockerfile
# ──────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS base

WORKDIR /app

# System deps:
#   - build-essential: compiling any C-extension Python deps (e.g. sentence-transformers stack)
#   - libpq-dev: psycopg2-binary / asyncpg runtime needs
#   - curl: container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# ── Dependencies (cached layer) ─────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

# Pre-download the local embedding model at build time so the first API
# request isn't stuck downloading ~130MB from the Hugging Face Hub.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# ── App code ─────────────────────────────────────────────────────────────
COPY . .

RUN mkdir -p /app/storage/reports

# Non-root user for the runtime
RUN groupadd --system app && useradd --system --gid app app \
  && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
