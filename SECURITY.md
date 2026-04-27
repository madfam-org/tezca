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

### TLS verification on government scrapers

Some Mexican government portals ship expired or misconfigured TLS chains. The allowlist of hosts where `verify=False` is acceptable lives in `apps/scraper/http.py:INSECURE_HOSTS`. Adding a host requires:

1. Documented justification (cert chain inspection, last-renewal date)
2. Per-host fingerprint pinning where feasible (Workstream 7 of the A+ plan tightens this from blanket bypass to fingerprint pinning)
3. Annual review of the allowlist — hosts that have since fixed their cert chains get removed

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
