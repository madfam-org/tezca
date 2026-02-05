# Monorepo Architecture

This repository is a **Polyglot Monorepo** containing both Python (Backend/Engine) and Node.js (Frontend) code.

## Structure

```
.
├── apps/               # Application-layer code
│   ├── indigo/         # Django API (Python)
│   ├── web/            # Next.js Frontend (Node.js)
│   └── parsers/        # AKN Parsers (Python)
├── engines/            # Logic Engines (Python)
│   ├── catala/         # Catala Source & Mock
│   └── openfisca/      # OpenFisca definitions
├── data/               # Legislative Data (XML/JSON)
├── docs/               # Documentation
└── scripts/            # Ingestion/Maintenance Scripts
```

## Management Strategy

### Python (Poetry)
The entire Python codebase is managed as a single Poetry project.
- **Root**: `pyproject.toml` defines dependencies for ALL Python apps.
- **Packages**:
    - `apps`: Contains API, Scrapers, Parsers.
    - `engines`: Contains Logical Units.
- **Run**: `poetry run python ...`

### Node.js (NPM Workspaces)
The frontend is managed via NPM Workspaces.
- **Root**: `package.json` defines the workspace `apps/*`.
- **Workspace**: `apps/web` is the primary workspace package.
- **Run**: `npm run dev --workspace=web` or `npm install` from root.

## Development Workflow

### 1. Unified Install
```bash
# Python
poetry install

# Node
npm install
```

### 2. Running Services
```bash
# Backend
poetry run python manage.py runserver

# Frontend
npm run dev --workspace=web
```

### 3. Docker (Production)
We use `docker-compose` to lift the entire stack, respecting these boundaries.
```bash
docker-compose up --build
```
