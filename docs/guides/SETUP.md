# Setup Guide

Complete installation and configuration guide for the Tezca pipeline.

## Prerequisites

- **Node.js**: 20+
- **Python**: 3.11+
- **Poetry**: Latest (`pip install poetry`)
- **Git**: For cloning repository
- **Redis**: 7+ (optional, for Celery task queue; falls back to threads without it)
- **Docker & Docker Compose**: For containerized deployment

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/madfam-org/tezca.git
cd tezca
```

### 2. Install Frontend Dependencies

```bash
npm install
```

This installs all workspace dependencies (web, admin, shared packages).

### 3. Install Backend Dependencies

```bash
poetry install
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (see .env.example for all variables)
```

Key variables:
- `DJANGO_SECRET_KEY` - Required, set to a random string
- `DB_ENGINE` - `django.db.backends.sqlite3` (default) or `django.db.backends.postgresql`
- `ES_HOST` - Elasticsearch URL (default: `http://localhost:9200`)
- `CELERY_BROKER_URL` - Redis URL for task queue (default: `redis://localhost:6379/0`)

### 5. Run Database Migrations

```bash
poetry run python manage.py migrate
```

### 6. Verify Installation

```bash
poetry run python -c "from apps.parsers import AkomaNtosoGeneratorV2; print('Installation successful!')"
```

## Development Servers

```bash
# Frontend: Public Portal (http://localhost:3000)
npm run dev:web

# Frontend: Admin Console (http://localhost:3001)
npm run dev:admin

# Backend: Django API (http://localhost:8000)
poetry run python manage.py runserver

# Optional: Celery worker (requires Redis)
poetry run celery -A apps.indigo worker --loglevel=info
```

## Docker Deployment (Local)

```bash
# Set required env vars
cp .env.example .env
# Edit .env (DJANGO_SECRET_KEY is required)

# Start all services
docker compose up -d
```

This starts: API, Celery worker, Web, Admin, PostgreSQL, Redis, Elasticsearch.

## Production Deployment (Tezca)

The production environment runs on the MADFAM ecosystem at **tezca.mx** using enclii (DevOps) and Janua (auth).

See the complete deployment guide: **[docs/deployment/PRODUCTION_DEPLOYMENT.md](../deployment/PRODUCTION_DEPLOYMENT.md)**

Key files:
- `enclii.yaml` — Service onboarding spec
- `deployment/enclii/` — 7 per-service specs
- `k8s/production/` — 16 K8s manifests (kustomization, deployments, services, PVCs)
- `.github/workflows/deploy-{api,web,admin}.yml` — CI/CD pipelines

## Running Tests

### Backend Tests

```bash
poetry run pytest tests/ -v
```

### Frontend Tests

```bash
npm run test --workspace=web
```

### Linting

```bash
# Python (must use poetry to match CI versions)
poetry run black --check apps/ tests/ scripts/
poetry run isort --check-only apps/ tests/ scripts/

# Frontend
npm run lint --workspace=web
npm run lint --workspace=admin
```

## Quick Start: Parse a Law

```python
from pathlib import Path
from apps.parsers import AkomaNtosoGeneratorV2

text = Path('data/raw/ley_amparo_extracted.txt').read_text()
parser = AkomaNtosoGeneratorV2()

metadata = parser.create_frbr_metadata(
    law_type='ley',
    date_str='2013-04-02',
    slug='amparo',
    title='Ley de Amparo'
)

xml_path, result = parser.generate_xml(text, metadata, Path('output/amparo.xml'))
print(f"Generated: {xml_path}")
print(f"Confidence: {result.metadata['confidence']*100:.1f}%")
```

## API Documentation

When the Django server is running:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Directory Structure

```
tezca/
├── apps/
│   ├── web/              # Public Portal (Next.js 15)
│   ├── admin/            # Admin Console (Next.js 16)
│   ├── api/              # Django REST API
│   ├── indigo/           # Django project settings
│   ├── parsers/          # AKN parsing pipeline
│   ├── scraper/          # DOF/OJN/Municipal scrapers
│   └── ingestion/        # Ingestion orchestration
├── packages/
│   ├── ui/               # Shared UI components (@tezca/ui)
│   ├── lib/              # Shared types & schemas (@tezca/lib)
│   └── tsconfig/         # Shared TS config
├── engines/
│   ├── catala/           # Tax algorithms
│   └── openfisca/        # Microsimulation
├── data/                 # Law registry, XMLs, logs
├── tests/                # Backend test suite (Pytest)
├── docs/                 # Documentation
├── pyproject.toml        # Python deps (Poetry)
└── package.json          # Workspace root (NPM)
```

## Troubleshooting

### Import Errors
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Redis Not Available
Celery tasks will fall back to thread-based execution. This is fine for local development.

### CI Lint Failures
Always use `poetry run black` / `poetry run isort` (not system versions) to match CI.

## Next Steps

- Read [Architecture Guide](../architecture/ARCHITECTURE.md)
- Review [Tech Stack](../architecture/TECH_STACK.md)
- Run [Tests](../../tests/)
- Check [Code Quality](code_quality.md)
