# Contributing to Tezca

Thank you for your interest in contributing to Tezca, the Mexican open law platform!

## Isomorphism Principle
This project adheres to the principle of **Isomorphism**: The code must be a faithful, verifiable representation of the law.

- **Lawyers**: Focus on `data/` (XML structure, law registries) and defining test cases.
- **Developers**: Focus on `apps/` (API, web, admin) and `scripts/` (pipeline, scraping).

## Workflow

1. **Pick a Task**: Check [ROADMAP.md](ROADMAP.md) for current priorities.
2. **Create a Branch**: `git checkout -b feat/your-feature` (never work on main).
3. **Implement**: Follow existing patterns in the codebase.
4. **Test**: Run the relevant test suites (see below).
5. **Lint**: Ensure formatting passes.
6. **Submit PR**: Link to relevant issue or data source in the PR description.

## Development Setup

```bash
npm install          # Frontend (all workspaces)
poetry install       # Backend (Python)
cp .env.example .env # Configure environment
```

## Testing

```bash
# Backend
poetry run pytest tests/ -v

# Web frontend
cd apps/web && npx vitest run

# Admin frontend
cd apps/admin && npx vitest run

# E2E
cd apps/web && npx playwright test
```

## Linting

```bash
# Python (MUST use poetry run for CI compatibility)
poetry run black --check apps/ tests/ scripts/
poetry run isort --check-only apps/ tests/ scripts/

# Frontend
npm run lint --workspace=web
npm run lint --workspace=admin
```

## Standards

- **Commits**: Follow Conventional Commits.
  - `feat(isr): encode article 93`
  - `fix(xml): typo in art 23 structure`
  - `feat(web): add compare diff highlighting`
- **Formatting**:
  - Python: Black (24.1+) + isort (profile=black)
  - TypeScript/JSX: ESLint + Prettier
- **Types**: Add shared types in `packages/lib/src/types.ts` + schemas in `schemas.ts`.
- **i18n**: All UI strings trilingual (ES/EN/NAH) using `useLang()` hook.
- **Design tokens**: Use `bg-muted`, `text-muted-foreground` (not raw Tailwind colors).
- **Components**: Use `@tezca/ui` primitives (Card, Badge, Button, etc.).

## Pull Request Process

1. Ensure all tests pass (`pytest`, `vitest`, `playwright`).
2. Ensure linting passes (`black`, `isort`, `eslint`).
3. Link to the official data source (DOF/OJN) in your PR description when applicable.
4. One approval required for merge.
