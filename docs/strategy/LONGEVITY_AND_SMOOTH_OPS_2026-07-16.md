# Tezca — Longevity & Smooth-Ops Plan (2026-07-16)

Recommendations for keeping tezca healthy with minimal recurring operator toil,
written after the 2026-07 stabilization session. Items marked **[done]** were
executed this session; **[queued]** are PRs/tasks in flight; **[operator]** need
a human action; **[roadmap]** are larger efforts to schedule.

## Guiding principle

Every recurring failure this session traced to one of three root causes:
1. **Silent pipelines** — scrapers reporting success while data never reached the DB.
2. **Expiring credentials** — PATs and npm tokens that break prod on a timer.
3. **Blind monitoring** — health checks that couldn't see 1 or 2.

Longevity = removing the recurrence, not just the instance.

## 1. Kill recurring credential expiry (biggest toil source)

- **[done]** Deploy pipeline de-PAT'd (#157): checkout + GHCR login now use the
  built-in `GITHUB_TOKEN`. Removes `MADFAM_BOT_PAT` from the deploy path entirely.
- **[operator]** One-time: link the 3 GHCR packages (`tezca/api|web|admin`) to the
  repo with Write via Actions-access UI, so `GITHUB_TOKEN` can push. After this,
  the API deploy has **zero** rotating-token dependency. (Issue #148.)
- **[operator/roadmap]** `NPM_MADFAM_TOKEN` still gates web/admin *image builds*
  (private `@janua`/`@tezca` packages). Two durable fixes, pick one:
  a. Move to a **non-expiring granular automation token** scoped read-only to those
     packages (npm supports this), or
  b. Vendor the private packages into the image via the git submodule + bot PAT
     clone pattern already used elsewhere (see `feedback_private_submodule_public_deploy`).
  Either ends the ~quarterly E401 fire drill.
- **[roadmap]** Add a Dependabot/renovate check or a scheduled workflow that warns
  30 days before any known token's expiry (npm tokens expose an expiry; surface it).

## 2. Make the data pipeline self-verifying (stop silent corpus freezes)

The 2026-07 wiring-gap audit found scrapers succeeding while nothing ingested.
- **[done]** RMF + treaty ingest scheduled (#156). NOM ingest command + schedule (#159).
- **[queued]** Row-growth health guard — `check_scraper_health` now flags
  "scrapes green but corpus rows flat across N runs" (the recurrence detector for
  this whole class). Once merged, a silent freeze pages instead of hiding.
- **[roadmap]** Remaining orphaned pipelines from the audit
  (`claudedocs/tezca-pipeline-wiring-audit-2026-07-15.md`): OJN/wayback recovery
  consumers, and the state-scraper format bridge (`catalog.json` →
  `state_laws_metadata.json`). The bridge also unblocks the 14→32 state-coverage
  push, which is the #1 competitive credibility gap.
- **[roadmap]** DOF auto-materialization (`DOF_AUTO_INGEST_ENABLED`) is wired but
  OFF everywhere; validate in staging then flip, else DOF-sourced changes stay frozen.

## 3. Observability that catches problems before users do

- **[verified]** `/health` endpoint exists and is wired to k8s liveness/readiness
  probes + the status page (`api.tezca.mx/health` → 200).
- **[roadmap]** Synthetic monitoring: an external check hitting `/health`,
  `/api/v1/laws/?page_size=1`, and `/api/v1/search/?q=...` on a schedule, alerting
  on non-200 or latency regression. This is the R5 item from the A+ plan and the
  cheapest insurance for a paid tier.
- **[roadmap]** Corpus-completeness dashboard (public): live per-category counts,
  last-updated timestamps, A–F grade distribution. Doubles as a competitive moat
  (competitors can't replicate without the pipeline) and an internal freeze alarm.

## 4. Dependency hygiene (reduce churn + supply-chain surface)

- **[done]** pip-audit gate un-stuck (#152); unused `juriscraper` dropped (#158,
  ended the recurring major-version bumps like #134).
- **[done]** Library-major-bump safety: the posthog v7 review (#155) caught a
  silent-telemetry regression. **Adopt as convention:** any dependabot *major* bump
  touching a wrapped SDK gets a "does the wrapper still bind?" review before merge,
  not an auto-merge.
- **[roadmap]** Keep the CVE SLO tight — the setuptools advisory landed mid-session
  and would have failed the next push; a weekly (not just on-PR) pip-audit +
  npm-audit scheduled run surfaces these before they block a deploy.

## 5. Deploy safety

- **[observation]** `main` has **no branch protection**. For a revenue-serving repo,
  add: require CI green + 1 review before merge to `main`. The admin-merge pattern
  used this session works because it's a solo operator with agent review, but a
  protection rule with an admin bypass is the durable version.
- **[done]** `GITHUB_TOKEN` digest commits don't re-trigger workflows → no more
  deploy-loop CI burn (side benefit of #157).

## Sequenced next actions (highest leverage first)

1. **[operator]** Link GHCR packages → dispatch Deploy API → today's backend fixes reach prod.
2. **[queued→merge]** Row-growth health guard.
3. **[operator]** Durable NPM token (granular non-expiring or submodule vendor) → web/admin deploys.
4. **[roadmap]** State-scraper format bridge → resume 14→32 coverage (the #1 competitive gap).
5. **[roadmap]** Synthetic monitoring + public completeness dashboard.
6. **[roadmap]** Branch protection on `main`.

Competitive context for prioritization: see
`COMPETITIVE_BENCHMARK_2026-04-27.md`. Buho is not the competitor (docket tracker);
the corpus-completeness + data-quality-transparency + API/MCP moats are where
longevity investment compounds against vLex/Tirant/Help-AI.
