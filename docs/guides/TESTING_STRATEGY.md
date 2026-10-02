# 🧪 TESTING_STRATEGY.md - Verification & Validation Protocols

> **SYSTEM NOTICE:** In this repository, "Green Builds" do not mean success. **Legal Accuracy** means success. A test that passes numerically but fails legally (e.g., applying a derogated rule) is a critical failure.

---

## 1. The "Oracle" Philosophy

We do not trust our own code. We trust the **Law** and the **Official Determinators**.

* **The Law:** The text in `data/federal/` is the absolute source of truth.
* **The Oracle:** Official government calculators (e.g., SAT simulators, IMSS SUA) are the "Oracle". If our code disagrees with the SAT's official simulator, our code is presumed wrong until proven otherwise.

---

## 2. Testing Layers

### Level 1: Structural Validation (XML)

Before logic, we validate the container.

* **Tool:** `xmllint` / `bluebell` validation.
* **Command:** `make validate-xml`
* **Check:**
* Does the Akoma Ntoso file conform to the OASIS schema?
* Are all `refersTo` tags resolving to valid Ontology IDs?
* **Crucial:** Does the `original_text` hash match the source PDF hash? (Integrity Check).



### Level 2: Unit Testing (The "Hypotheticals")

Every logical function must have corresponding unit tests representing "Judicial Hypotheticals."

#### 2.1 Catala (Fiscal Logic)

Catala has built-in testing. We use **Scope-based testing**.

* **Location:** `engines/catala/tests/`
* **Method:** Define a `scope` with inputs mimicking a real taxpayer.
* **Example:**
```catala
# Test Case: Resico 2024 - Low Income
scope TestResico:
  input income: 200000 MXN
  assertion tax_due = 2000 MXN # 1.0% rate

```


* **Requirement:** Every tax bracket in the *Anexos de la Resolución Miscelánea Fiscal* must have at least one test case hitting it (100% Branch Coverage).

#### 2.2 Blawx (Rule Logic)

We test logic using "Queries" against known scenarios.

* **Method:** Create a "Fact Scenario" (e.g., "Juan killed Pedro in self-defense").
* **Assertion:** The query `is_guilty(Juan)` must return `FALSE`.

### Level 3: Regression Testing (The "Time Travel" Check)

Law changes over time. New code must not break old years.

* **The Golden Rule:** When you implement the *Reform of 2024*, you must run the test suite for **2023** and **2022**. The results for those years must remain **identical**.
* **Implementation:** We maintain snapshots of calculated outputs for standard personas ("Persona A", "Persona B") for every fiscal year.

---

## 3. The "Legislative Trace" (Explanation Test)

A correct answer is useless without a correct citation.

* **Requirement:** The API response must include a `trace` object.
* **Test:**
* Input: Calculate ISR.
* Output: `$5,000`.
* Trace Check: Does the output list `LISR Art. 93` as a used variable? If the code used an exemption but didn't cite the article, the test **fails**.



---

## 4. Dataset & Benchmarks

We do not use random numbers. We use **Canonical Legal Personas**.

| Persona ID | Description | Usage |
| --- | --- | --- |
| `p_asalariado_min` | Minimum wage worker | Test subsidy mechanics (*Subsidio al Empleo*) |
| `p_resico_limite` | Freelancer earning $3.5M | Test the "exit condition" of RESICO regime |
| `p_moral_lucro` | Standard SA de CV | Test Coeficiente de Utilidad |
| `p_border_zone` | Worker in Tijuana | Test 8% IVA / Border Stimulus |

**Agent Directive:** When writing a new test, import these personas from `tests/fixtures/personas.json`. Do not invent "John Doe" with arbitrary numbers.

---

## 5. CI/CD Gatekeepers

Code cannot merge to `main` unless:

1. **Syntax:** XML and Python linting passes.
2. **Logic:** All Catala proofs verify.
3. **Accuracy:** Output matches the "Oracle" dataset (scraped results from SAT) within a $0.01 MXN tolerance.
4. **Legal Review:** (Human Step) A maintainer with the `legal-reviewer` tag approves the interpretation.

---

## 6. Current Test Infrastructure

### Backend (Pytest)
- **Location:** `tests/`
- **Run:** `PYTHONPATH=apps:. poetry run pytest tests/ -v`. CI adds `--cov=apps --cov-fail-under=60` (actual 69.36% on 2026-10-01).
- **Result on 2026-10-01** (Python 3.11, no extras, SQLite): `3025 passed, 18 skipped`.
- **Lint:** `poetry run black --check apps/ tests/ scripts/` + `poetry run isort --check-only apps/ tests/ scripts/`. Always use `poetry run black` (26.x, from `poetry.lock`), not a system black.
- **Other gates in the same job:** `makemigrations --check`, `scripts/utils/audit_file_sizes.py` (>800 LOC fails), `scripts/utils/audit_silent_excepts.py`, `pip-audit`.
- **Dependency floors:** `tests/test_dependency_floors.py` fails if `poetry.lock`, `pyproject.toml`, `packages/mcp-server/uv.lock` or `package-lock.json` drops below a security floor (see `SECURITY.md`). It also fails if `poetry.lock` resolves to a release PyPI has yanked (pypdfium2 5.12.0).

#### Skipped tests, and why
CI does not install the optional extras (`pdf`, `export`, `ocr`, `r2`, `production`), and it has no Elasticsearch or PostgreSQL in `test-backend`. Every skip below is environmental. None hides a known bug.

| Where | Skips when | Why it is acceptable |
|---|---|---|
| `tests/api/test_api.py::CalculationApiTests` | always (`@pytest.mark.skip`) | The OpenFisca calculation engine is not installed. The suite stays as the contract for when it is. |
| `tests/api/test_storage.py` (R2 backend) | `boto3` missing (`-E r2`) | The local backend is tested unconditionally. |
| `tests/scraper/test_scjn_playwright.py`, `tests/scraper/test_scheduling_tasks.py::TestPlaywrightTasks` | real `playwright` missing (`-E production`) | These need the browser driver. |
| `tests/integration/test_db_es_consistency.py` | Elasticsearch unreachable or index empty | Integration checks against a live stack. `xfail`s only report laws with parse failures. |
| `tests/api/test_ingest_jcf.py` (domain-filter branch) | database is not PostgreSQL | The JSONField branch is PostgreSQL-only. The engine-independent `test_domains_field_is_the_routing_key_for_labor_consumers` covers the routing key. `test-publication-postgres` does not include this file, so the PostgreSQL branch runs only locally. |

#### Known flaky
- `tests/api/test_prometheus_metrics.py::TestUnderGunicorn::test_master_serves_the_sum_of_all_workers`: it counts requests across gunicorn workers and has once read 21 instead of 20. It passes on a rerun. Rerun before you investigate.
- `tests/integration/test_spot_check.py` together with `tests/pipeline/test_index_laws.py`: a fixture-pollution flake that fails them only when they run in the same invocation. Each passes alone. The full 2026-10-01 run passed with both included.

#### PDF export (`GET /api/v1/laws/<id>/export/pdf/`)
- `tests/api/test_export_views.py` covers access (anonymous 403, tier limits) and the 501 answer without WeasyPrint.
- `tests/api/test_export_pdf_render.py` covers the success path:
  - it renders the real `export/law_pdf.html`;
  - it checks the exact `HTML(string=...).write_pdf()` call, the `application/pdf` response and its filename, that article text is escaped, and the `ExportLog` row.
  - WeasyPrint itself is replaced there, because CI has no Pango.

##### PDF export rendering (manual check)
CI cannot catch a broken WeasyPrint/pydyf pairing. WeasyPrint 62.3 with pydyf 0.12.1 raised `AttributeError` in `write_pdf()` until #263 moved WeasyPrint to 70.0. After you bump `weasyprint` or `pydyf`, render the real template once on a machine with Pango ≥ 1.44 (`brew install pango`, or `apt-get install libpango-1.0-0 libpangocairo-1.0-0`). The API image already has Pango and WeasyPrint.

```bash
poetry install -E pdf
poetry run python - <<'EOF'
import django
from django.conf import settings
settings.configure(TEMPLATES=[{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": ["apps/api/templates"],
}])
django.setup()
from django.template.loader import render_to_string
from weasyprint import HTML

articles = [{"article": str(i), "text": f"Texto del artículo {i}. " * 40} for i in range(1, 120)]
html = render_to_string("export/law_pdf.html", {
    "law_name": "Ley de prueba", "official_id": "prueba", "tier_label": "Federal",
    "category": "ley", "state": None, "status": "vigente", "publication_date": None,
    "article_count": len(articles), "articles": articles, "generation_date": "2026-10-01 12:00",
})
open("/tmp/law.pdf", "wb").write(HTML(string=html).write_pdf())
print("ok")
EOF
```

Open `/tmp/law.pdf`. Check that it has several pages, the `@top-center` header and the `Pág. N de M` footer. After the deploy, run check 13 in `docs/deployment/PRODUCTION_DEPLOYMENT.md`.

### MCP server (`packages/mcp-server`, pytest + respx)
- **Run:** `cd packages/mcp-server && uv sync --all-extras && uv run pytest tests/ -v`. CI runs it in `test-mcp`.
- **Result on 2026-10-01:** `25 passed, 8 skipped`. The 8 are the live-API tests in `tests/test_integration.py`, which skip unless `TEZCA_API_URL` points at a real API.
- `tests/test_app.py` imports `main`, calls `GET /health` and checks that `/mcp` is mounted. Before it existed, Starlette 1.0's removal of `@app.route` broke `import main` while the suite stayed green.

### Web Frontend (Vitest)
- **Location:** `apps/web/__tests__/`
- **Tests:** 229 tests across 33 files
- **Run:** `cd apps/web && npx vitest run`
- **Coverage:** `cd apps/web && npx vitest run --coverage` (uses @vitest/coverage-v8)
- **Coverage thresholds:** statements 60%, branches 50%, functions 60%, lines 60%
- **Framework:** Vitest + @testing-library/react
- **Key test areas:** search, laws, compare, dashboard, categories, states, CommandSearch, FeaturedLaws, ExportDropdown, CrossReferencePanel, VersionTimeline, RelatedLaws

### Admin Frontend (Vitest)
- **Location:** `apps/admin/__tests__/`
- **Tests:** 51 tests across 8 files
- **Run:** `cd apps/admin && npx vitest run`
- **Framework:** Vitest + @testing-library/react
- **Key test areas:** useApiData hook, API client, home/metrics/settings/dataops/ingestion/roadmap pages
- **Mocking:** `@tezca/ui` and `next/link` mocked inline via `vi.mock()`

### E2E (Playwright)
- **Location:** `apps/web/e2e/`
- **Tests:** 8 specs (search, law-detail, comparison, bookmarks, language, filters, navbar, 404)
- **Run:** `cd apps/web && npx playwright test`
- **Browser:** Chromium (auto-starts dev server, mocks API via `page.route()`)

### CI Pipeline (`.github/workflows/ci.yml`)
- **Jobs:** `test-backend` + `test-frontend` (parallel) → `test-e2e` (advisory, needs both)
- **Coverage artifacts:** pytest XML + vitest JSON uploaded per run
- **E2E artifacts:** Playwright HTML report uploaded on failure
- **Deploy:** 3 deploy pipelines (web, admin, API) via GHCR + ArgoCD

> **Note:** The computational law testing layers (Catala proofs, Oracle validation, Legislative Trace) described above are aspirational design targets. The current test suite covers API endpoints, parser functionality, scraper logic, and React components.

*Last verified: 2026-10-01 (backend and MCP server sections); frontend counts last verified 2026-02-07*
