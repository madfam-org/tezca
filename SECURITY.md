# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Tezca, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email security@madfam.io with details
3. Include steps to reproduce if possible
4. We will acknowledge receipt within 48 hours

## Sensitive Data

This project handles sensitive Mexican legal data including:
- Laws, regulations, and jurisprudence
- API keys and access tokens
- User search history and preferences
- Cached legal document content

### Rules

- API keys and tokens must **never** be committed to version control
- User search history must be stored encrypted at rest
- All API endpoints require authentication
- Logs must never contain passwords, tokens, or user search queries

## Supply Chain Security

### Image signing

All deploy commits push `@sha256:`-pinned digests. Kyverno fail-closes any manifest that uses `:latest` or mutable tags. See `internal-devops/ECOSYSTEM.md` for the cluster-wide policy.

### Dependency CVE SLO

We commit to the following service level objective on dependency vulnerabilities:

| Severity | Patch SLO | Track via |
|---|---|---|
| Critical (CVSS ≥9.0) | 24 hours | manual triage on Dependabot alert |
| High (CVSS 7.0–8.9) | 7 days | weekly Dependabot PRs (`.github/dependabot.yml`) |
| Medium (CVSS 4.0–6.9) | 30 days | weekly Dependabot PRs |
| Low (CVSS <4.0) | next minor release | weekly Dependabot PRs |

**Measurement:** any merged PR with title prefix `fix(deps):` (e.g. PR #42) counts as a CVE remediation. The CI gates `pip-audit` and `npm audit --audit-level=high` against the locked deps before every merge. A high-severity CVE that lingers >7 days without a tracked Dependabot PR triggers a manual operator review.

**Operator runbook:** monthly `pip-audit && npm audit` reconciliation against open Dependabot alerts; investigate any drift. Tracked in `internal-devops/audits/`.

### Security baseline (2026-09-30)

The minimum versions below are security floors. Raise them, never lower them.
`tests/test_dependency_floors.py` fails the backend test job if `poetry.lock`,
`pyproject.toml`, `packages/mcp-server/uv.lock` or `package-lock.json` drifts
below any of them.

| Package | Floor | Why |
|---|---|---|
| `next` (`apps/web`, `apps/admin`) | 16.3.8 | GHSA-vcvr-r3jv-pc5j, a critical RCE in `next/og` `ImageResponse` (`>=16.2.0 <16.3.6`). `apps/web` serves a dynamic `next/og` route, `/leyes/[id]/opengraph-image`. Bumped in #258. |
| `axios` (root `package-lock.json`) | 1.20.0 | High-severity npm audit findings on 1.19.0. Bumped in #259. |
| `PyJWT` | 2.15.1 (`^2.15.1` in `pyproject.toml`) | pip-audit findings on 2.13.0. Bumped in #259. |
| `urllib3` | 2.8.0 (`>=2.8,<3` in `pyproject.toml`) | pip-audit findings on 2.7.0. Bumped in #259. |
| `weasyprint` (`pdf`/`export`/`production` extras) | 70.0 (`^70.0` in `pyproject.toml`) | GHSA-983w-rhvv-gwmv (SSRF via redirect, fixed in 68.0), GHSA-jf6q-chmf-3h3v (SSRF, fixed in 70.0), GHSA-jhhc-3hcp-qhm5 (CSS injection, last affected 68.1). No 62.x release carries the fixes. |
| `packages/mcp-server/uv.lock` | PyJWT 2.15.1, mcp 1.30.0, starlette 1.7.0, python-multipart 0.0.32, cryptography 50.0.2, anyio 4.15.1 | Lockfile floors for the MCP server (GHSA-ffc3-869f-jxw9 and the other PyJWT 2.12–2.14 advisories, the mcp 1.27–1.28 transport advisories, starlette, python-multipart, cryptography and anyio advisories). They are transitive through `mcp`, so they live in the lockfile only. |

The same test refuses releases that PyPI has yanked. pypdfium2 (through
`pdfplumber`) moved from the yanked 5.12.0 to 5.12.1 on 2026-10-01.

WeasyPrint 70.0 also fixed PDF export. 62.3 with the locked pydyf 0.12.1
raised `AttributeError` inside `write_pdf()`. See Gotcha 13 in
[`docs/deployment/PRODUCTION_DEPLOYMENT.md`](docs/deployment/PRODUCTION_DEPLOYMENT.md#gotchas).

**A root lockfile change does not redeploy web or admin.** `deploy-web.yml` and
`deploy-admin.yml` run on pushes under `apps/web/**` / `apps/admin/**`,
`packages/ui/**` and `packages/lib/**` only. A fix that touches nothing but the
root `package-lock.json` (as #259's axios bump did) is merged but not shipped.
Ship it with a manual dispatch of each workflow:

```bash
gh workflow run deploy-web.yml   -R madfam-org/tezca -f deploy_ack=production -f reason="ship root lockfile fix <sha>"
gh workflow run deploy-admin.yml -R madfam-org/tezca -f deploy_ack=production -f reason="ship root lockfile fix <sha>"
```

`deploy_ack` must be `production` and `reason` at least 12 characters. The
API image, which the worker and beat Deployments also run, does redeploy on
`pyproject.toml` / `poetry.lock` changes (`deploy-api.yml`). Full trigger table:
[`docs/deployment/PRODUCTION_DEPLOYMENT.md`](docs/deployment/PRODUCTION_DEPLOYMENT.md#cicd).

### TLS verification on government scrapers

Some Mexican government portals ship expired or misconfigured TLS chains. `apps/scraper/http.py` resolves trust through two layers:

1. **`HOST_FINGERPRINTS`** — preferred. The host's leaf cert SHA-256 is compared against a pinned value at connection time. A mismatch fails the connection (no fallback). Pinning a host requires capturing the fingerprint with `scripts/utils/capture_tls_fingerprint.py <host>`. Pinned hosts are reviewed annually or whenever a connection is rejected.

2. **`INSECURE_HOSTS`** — fallback for chains too unstable to pin (e.g. multi-balancer rotations). Adding a host requires:
   - Documented justification (cert chain inspection, last-renewal date)
   - A capture attempt — if the leaf is stable, fingerprint instead
   - Annual review — hosts that fix their chains are removed

Hosts not in either set get normal CA-verified TLS. Test coverage in `tests/scraper/test_http.py` exercises both trust paths.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
