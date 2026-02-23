# apps/indigo/Dockerfile — Django API + Celery
# Build context: project root (monorepo)

# ── Stage 1: Builder ─────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

# System dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    pkg-config \
    libgmp-dev \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock ./

# Install Python dependencies into .venv
RUN poetry install --no-interaction --no-ansi --no-root -E production

# Download spaCy model
RUN poetry run python -m spacy download es_core_news_sm

# ── Stage 2: Runtime ─────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Runtime-only system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    libgmp10 \
    wget \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --system --gid 1001 django && \
    useradd --system --uid 1001 --gid django django

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /app/.venv ./.venv

# Copy application code
COPY . .

# Collect static files (needs Django available)
RUN python apps/manage.py collectstatic --noinput 2>/dev/null || true

# Create directories for runtime data
RUN mkdir -p /app/staticfiles /app/logs && \
    chown -R django:django /app/staticfiles /app/logs

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/api/v1/admin/health/ || exit 1

# Gunicorn with gthread for async-compatible workers
CMD ["gunicorn", "apps.indigo.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
