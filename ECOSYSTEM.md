# tezca — Ecosystem Context

> **Mexican law oracle — machine-readable federal/state/municipal laws, rulings, and DOF feeds.**

This file is self-contained: a Claude session on a fresh machine can operate
this service by reading only this one document. No external links are
load-bearing — the MADFAM ecosystem map and the full enclii CLI reference are
embedded below.

---

## 1. What this repo is

Tezca is the informational source of truth for Mexican law. It ingests and indexes DOF publications, SCJN rulings, SAT guidance, and federal/state/municipal statutes into a machine-readable catalog. Tezca is purely an oracle — it does NOT generate contracts, sign documents, or touch client engagements. **Karafiel** consumes Tezca's feeds and operationalizes them (template updates, CFDI rule changes, compliance checks).

**Pillar**: Legal / Intelligence (informational)
**Type**: service
**Status**: production

### Deployed services

| Service | Public domain | Container port |
|---|---|---|
| `tezca-web` | tezca.mx | 3000 |
| `tezca-api` | api.tezca.mx | 8000 |
| `tezca-admin` | admin.tezca.mx | 3001 |

**Kubernetes namespace**: `tezca`
**Cluster**: bare-metal k3s on Hetzner (see topology section below).

### Upstream dependencies (this repo consumes)

- postgres (catalog — laws, rulings, DOF feed)
- elasticsearch (full-text search)
- celery + redis (ingestion workers)
- madfam-crawler (scraping-as-a-service for scrapers)
- external: DOF publisher feeds, SCJN, SAT
- janua (admin/api auth)

### Downstream consumers (this repo is consumed by)

- karafiel (operationalizes rulings into CFDI/NOM-151 templates)
- tezca-mcp (MCP server for AI agents under `packages/mcp-server`)
- public web portal at tezca.mx

### Key environment variables

- `DATABASE_URL — Postgres catalog`
- `ELASTICSEARCH_URL — search index`
- `REDIS_URL — Celery broker`
- `JANUA_JWKS_URI — auth token verification`
- `CORS_ALLOWED_ORIGINS — explicit allowlist (no wildcards post-H2 audit)`

---

## MADFAM Ecosystem Map

MADFAM runs ~40 services on sovereign bare-metal infrastructure. Everything
below is embedded here so this document stands alone.

### The platforms every repo should know about

| Platform | Repo | Role |
|---|---|---|
| **Enclii** | `madfam-org/enclii` | PaaS control plane — all deploys go through this |
| **Janua** | `madfam-org/janua` | OIDC/OAuth 2.0 provider — RS256 JWKS at `auth.madfam.io/.well-known/jwks.json` |
| **Dhanam** | `madfam-org/dhanam` | Billing + payment gateways (Stripe, Mercado Pago, SPEI, etc.) |
| **Selva** | `madfam-org/autoswarm-office` | LLM inference routing + agent orchestration |
| **Karafiel** | `madfam-org/karafiel` | Operational compliance — CFDI, NOM-151, e.firma, SAT-adjacent. Owns legal-ops / contract templates |
| **Tezca** | `madfam-org/tezca` | Mexican law oracle (informational only — feeds Karafiel) |
| **Cotiza** | `madfam-org/digifab-quoting` | MADFAM's quoting engine (fabrication + services) |
| **Forgesight** | `madfam-org/forgesight` | Digital fabrication industry intelligence (pricing/vendor feed to Cotiza) |
| **Pravara MES** | `madfam-org/pravara-mes` | Fabrication-node routing and dispatch (physical jobs) |
| **PhyneCRM** | `madfam-org/phyne-crm` | Client-facing deliverables portal (single pane of glass per engagement) |
| **Fortuna** | `madfam-org/fortuna` | Problem intelligence / zeitgeist analysis |
| **Avala** | `madfam-org/avala` | Learning verification platform |

### Cross-repo conventions

- **Auth**: every authenticated service verifies Janua JWTs via JWKS at
  `https://auth.madfam.io/.well-known/jwks.json`. RS256 only — HS256 is
  fail-closed after the 2026-04-23 audit (H3/H4).
- **Billing**: credit metering + entitlements flow through Dhanam. See
  `madfam-org/dhanam` for the meter/entitlement/invoice APIs.
- **Inference**: every LLM call should route through Selva
  (`autoswarm-office`) at `/v1` (OpenAI-compatible). Do not talk directly
  to OpenAI / Anthropic from service code.
- **CORS**: explicit allowlist per service. Wildcards are banned
  (audit 2026-04-23 H2/H5/H6).
- **Images**: `@sha256:`-pinned in every manifest. Kyverno fail-closes on
  `:latest` or mutable tags.
- **Onboarding**: `POST /v1/admin/onboard` on switchyard-api creates
  namespace, ArgoCD app, Cloudflare tunnel routes, Janua client, and
  NetworkPolicies in one shot. See `enclii/docs/guides/ONBOARDING_GUIDE.md`.

### Production topology

Bare-metal k3s (v1.33+) on Hetzner, 3 nodes:

- `foundry-cp` (Hetzner EX44, 14C/20T, 128 GB) — control-plane + primary workload
- `foundry-worker-01` (Hetzner AX41-NVMe, Ryzen 5 3600, 64 GB) — worker + Longhorn 2nd replica
- `foundry-builder-01` (Hetzner VPS, 2 vCPU, 4 GB, tainted `builder=true:NoSchedule`) — ARC runners only

**Ingress**: Cloudflare Tunnel → 2× cloudflared pods → K8s ClusterIP → container port.
Zero exposed node ports. TLS terminated at Cloudflare edge.

**Storage**: Longhorn CSI v1.7+ in 2-replica mode across dedicated nodes.
Object storage: Cloudflare R2 (zero egress).

**GitOps**: ArgoCD App-of-Apps (~28 apps across ~22 namespaces) with self-heal.
Push to `main` → CI builds → GHCR → `kustomize edit set image` commits digest →
ArgoCD syncs → Switchyard tracks lifecycle events.

**Operational access** (SSH, kubeconfigs, server IPs, cost ledger): private repo
`madfam-org/internal-devops`. Not in any public repo.

---

## Enclii CLI — DevOps Reference

**Strong preference: use `enclii` over `kubectl`** for all operational
tasks. The CLI routes through Switchyard API, which gives you audit
logging, lifecycle event tracking, and service-scoped context. Escape
to kubectl only for the gaps listed at the end of this section.

### Install

```bash
# macOS
brew install enclii/tap/enclii

# Linux
curl -sSL https://get.enclii.dev | bash

# From source (in the enclii repo)
make build-cli && ./bin/enclii --version
```

### Auth

```bash
enclii login                  # browser SSO (Janua)
enclii whoami                 # verify active session
enclii logout                 # clear local creds
```

Env vars: `ENCLII_API_URL` (default `https://api.enclii.dev`),
`ENCLII_TOKEN` (alternative to interactive login),
`ENCLII_PROJECT`, `ENCLII_ENV`.

### Day-to-day for tezca-api

The commands below default to `tezca-api` — the primary service name for
this repo as registered in Switchyard. For any other service in the
ecosystem, swap the name.

```bash
# Status + where the pods are running
enclii ps --wide
enclii ps tezca-api --env production

# Logs (tail, filter, history)
enclii logs tezca-api -f                          # live tail
enclii logs tezca-api --since 1h --level error    # last hour, errors only
enclii logs tezca-api --env staging -f

# Deploy (preview, staging, production)
enclii deploy --env preview                       # from current branch
enclii deploy --env staging
enclii deploy --env production --strategy canary --canary-percent 10

# Rollback
enclii rollback tezca-api                         # previous release
enclii rollback tezca-api --to-revision 5

# Releases + history
enclii releases tezca-api                          # list builds
enclii releases tezca-api --latest --output json

# Secrets (routed through Lockbox → Vault → ESO → K8s)
enclii secrets list tezca-api
enclii secrets set MY_KEY=value --service tezca-api --secret
enclii secrets rm MY_KEY --service tezca-api

# Domains, tunnel routes, DNS
enclii domains list tezca-api
enclii domains add tezca-api my.example.com       # auto-provisions tunnel route + DNS

# Scheduled jobs (cron + one-off)
enclii jobs list
enclii jobs run <job-name>                         # trigger one-off

# Routing (ingress + TLS)
enclii junctions list tezca-api

# Serverless (scale-to-zero functions)
enclii functions list

# Local dev environment
enclii local up         # spin up dependent services (postgres, redis, …)
enclii local logs
enclii local down
```

### Full onboarding (only used when adding a brand-new service)

```bash
# One-shot: namespace + ArgoCD app + tunnel routes + Janua client + netpol
enclii onboard --repo madfam-org/<name> --db-name <db> --secrets-file .env
```

### When to use kubectl (escape hatches)

The enclii CLI routes through Switchyard. These operations don't yet have
a CLI equivalent — kubectl is the right tool:

- ArgoCD sync / patch — `kubectl patch application <app> -n argocd --type merge ...`
- Kyverno PolicyExceptions + raw CRD management
- Longhorn / PVC operations — `kubectl get volumes.longhorn.io -n longhorn-system`
- Direct pod exec for debugging — `kubectl exec -n <ns> deploy/<svc> -- ...`
- Raw port-forward — `kubectl port-forward -n <ns> svc/<svc> 8080:80`
- Janua DB ops (no enclii equivalent)

### Cluster access

kubeconfig + SSH keys live in `madfam-org/internal-devops` (private repo).
On a fresh machine, pull that repo first to get `~/.kube/config-hetzner`.

### Exit codes (scripting against the CLI)

| Code | Meaning |
|---|---|
| 0  | success |
| 10 | validation error |
| 20 | build failed |
| 30 | deploy failed |
| 40 | timeout |
| 50 | auth error |

---

## Document provenance

Generated 2026-04-23 as part of the "each repo stands alone" docs sweep. If the
ecosystem map or CLI reference drifts from reality, update the generator at
`madfam-org/enclii/docs/templates/ECOSYSTEM.md.template` and re-render — don't
edit per-repo copies in isolation.
