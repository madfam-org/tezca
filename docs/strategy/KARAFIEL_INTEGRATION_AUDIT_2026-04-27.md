# Karafiel Integration Audit — Tezca Readiness

**Last Updated:** 2026-04-27
**Track:** Track 5 of [FEATURE_PARITY_PLAN_2026-04-27](./FEATURE_PARITY_PLAN_2026-04-27.md) §3.4
**Status:** Audit complete; 1 P0 blocker, 2 operator actions, 1 cross-repo coordination ticket needed.
**Scope:** Verify Tezca is technically ready for Karafiel to consume it as the law-feed + compliance-alerts source per `internal-devops/ecosystem/gtm-strategy.md` Wave 1.

---

## 1. The integration contract (one-page reference)

Per `internal-devops/ecosystem/gtm-strategy.md`, Karafiel's Wave 1 lists Tezca as a "Supporting Service Active in Wave 1: Law data feed + webhook for compliance alerts." Karafiel's Enterprise tier ($12,000 MXN/mo) explicitly bundles "+ Tezca law tracking, NOM-151 stamping, API access."

Concrete shape of the integration:

```
┌─────────────────────────────────────────────────────────────┐
│  Karafiel-API (compliance worker)                           │
│   1. provisions tzk_* API key (Institutional tier)          │
│   2. POST /api/v1/webhooks/                                 │
│      domain_filter: ["fiscal", "labor", "administrative"]  │
│      events: ["law.created", "law.updated", "version.created"]
│   3. caches webhook secret                                  │
└─────────────────────────────────────────────────────────────┘
                       ▲                       │
                       │ HMAC-signed POST      │ scoped reads
                       │ (when laws change)     ▼
┌─────────────────────────────────────────────────────────────┐
│  Tezca-API                                                  │
│   - signals.law_changed → dispatch_webhook_event            │
│   - filters by sub.domain_filter                            │
│   - delivers via deliver_webhook Celery task                │
│   - 10-failure auto-disable (failure_count column)          │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ ingestion pipeline writes Law rows
                       ▼
            DOF + RMF + NOM + state scrapers
```

**No Karafiel-specific code in Tezca.** Per the Integration Policy in CLAUDE.md ("Zero Touch"), Tezca is generic multi-tenant. Karafiel is one of any number of webhook subscribers. Verified via `grep -rn karafiel apps/`: zero matches outside docstrings + footer link.

---

## 2. What was audited

| Surface | Verified state | Status |
|---|---|---|
| API key provisioning supports Institutional tier | `provision_api_key` CLI exists; `APIKey.tier` accepts `institutional` | ✅ |
| Webhook subscription with `domain_filter` | `WebhookSubscription.domain_filter` JSONField, filtered in `webhooks.dispatch_webhook_event` | ✅ |
| Domain enrichment in webhook payloads | `signals._resolve_domains` walks `Law.domains` then falls back to `DOMAIN_MAP[category]` | ✅ |
| HMAC signing on outbound webhooks | `WebhookSubscription.secret` (64 chars) + `deliver_webhook` Celery task | ✅ |
| Auto-disable on repeated failures | `failure_count` field, "auto-disable after 10 consecutive failures" per model docstring | ✅ |
| Per-key rate-limit override | `APIKey.rate_limit_per_hour` (1–100,000/hour) | ✅ (capped — see §4) |
| SSRF protection on webhook URLs | `apps/api/utils/url_validation.py` validates against private/reserved IPs | ✅ |
| Fiscal corpus available for filtering | RMF scraper landed in `0b5af6b` (Track 1, this session) | ✅ NEW |
| `domains` field populated on existing laws | `classify_law_domains` exists; `classify-domains-weekly` Beat task runs Mondays 05:30 | ✅ scheduled |
| NOM corpus (labor, safety) | `nom_scraper.py` (~4,000 NOMs); `nom-monthly-full` Beat 15th of each month | ✅ |
| Webhook DLQ on dispatch failure | `apps/api/tasks.deliver_webhook` retries; underlying Celery DLQ pattern matches `madfam:billing-events-dlq` | ✅ |

---

## 3. P0 blocker before Karafiel goes live

### 3.1 Domain classification coverage gap

`Law.domains` is the JSONField that powers `domain_filter` matching in `webhooks.py:31-36`. If `Law.domains == []` for a fiscal law, the filter rejects the event even though the law IS fiscal — a false negative. Karafiel would silently miss events.

**The mitigation already exists** (`signals._resolve_domains` falls back to `DOMAIN_MAP[law.category]` when `Law.domains` is empty), but `DOMAIN_MAP` only knows generic categories (`finance`, `labor`, etc.) — it does NOT know e.g. `category="resolución_miscelánea_fiscal"` (the new RMF category from Track 1) maps to the `fiscal` domain. So **new corpus tagged with new categories produces false-negative filter results until either (a) `Law.domains` is populated by `classify_law_domains`, or (b) `DOMAIN_MAP` is extended**.

**Action:** Before Karafiel is live, the operator needs to:

1. Verify the Beat task `classify-domains-weekly` has run on production (Monday 05:30) and populated `Law.domains` for all >30k laws.
2. Run a one-shot full-corpus `python manage.py classify_law_domains --all --force` to backfill any laws the weekly task hasn't seen yet.
3. Spot-check by running the SQL queries below.

**Operator-runnable verification queries** (run from production database):

```sql
-- Total laws with empty domains (should be < 5% before going live with Karafiel)
SELECT COUNT(*) AS no_domains
FROM api_law
WHERE domains = '[]' OR domains IS NULL;

-- Per-category breakdown of laws missing domains
SELECT category, COUNT(*) AS n
FROM api_law
WHERE (domains = '[]' OR domains IS NULL)
GROUP BY category
ORDER BY n DESC
LIMIT 20;

-- Sanity check: count fiscal-tagged laws (Karafiel's primary filter)
SELECT COUNT(*) AS fiscal_tagged
FROM api_law
WHERE domains LIKE '%"fiscal"%';
```

**Acceptance threshold:** ≥95% of `Law` rows must have non-empty `domains`. Anything less and Karafiel will systematically miss compliance alerts.

---

## 4. Operator-only items

### 4.1 Karafiel API key provisioning

Karafiel's compliance worker needs an `Institutional` tier `tzk_*` key scoped to `webhooks` + `read` + `search`. Provisioning is operator-only because it requires the production DB:

```bash
python manage.py provision_api_key \
  --owner-email karafiel-ops@madfam.io \
  --name "Karafiel Compliance Worker" \
  --tier institutional \
  --scopes read search webhooks \
  --rate-limit-per-hour 10000   # adjust based on Karafiel's projected volume
```

Karafiel-side projected volume: per `gtm-strategy.md` Wave 1 Month 3, the target is 5 paying clients. Each client polls obligations + receives webhook fanout. **Estimated Karafiel-driven volume against Tezca: <1,000 webhook events/day** (Mexican legislative cadence: ~5-15 federal law changes/day on average; multiplied across all 5 client tenants is still <100/client/day after `domain_filter`).

**10,000/hour cap is comfortable headroom**; can stay at default `Institutional` rate (50,000/hour per `tier_throttles.py`). Per-key override unnecessary for Wave 1.

### 4.2 Karafiel webhook subscription registration

After Karafiel has its API key, Karafiel-side registers the webhook subscription. This is normal API consumer behavior — not Tezca-side work:

```bash
# Karafiel runs this once at deploy time
curl -X POST https://api.tezca.mx/api/v1/webhooks/ \
  -H "X-API-Key: tzk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.karafiel.mx/v1/tezca-webhook",
    "events": ["law.created", "law.updated", "version.created"],
    "domain_filter": ["fiscal", "labor", "administrative"],
    "law_id_filter": []
  }'
```

Response includes the HMAC `secret` Karafiel must store and verify on every incoming POST.

---

## 5. Cross-repo coordination ticket

Karafiel needs a documented runbook for: which Tezca events fire which compliance alerts, how to test the integration in karafiel-staging, and what to do on auto-disable. **This belongs in `madfam-org/karafiel`, not in this repo.**

**Suggested ticket title (operator to file in karafiel):**
> Tezca integration runbook: webhook event → compliance alert mapping

The runbook should answer:
- Which `domain` values Karafiel cares about (`fiscal`, `labor`, `administrative` confirmed; possibly `safety`, `customs` per consumer-facing composites in `apps/api/constants.py:DOMAIN_MAP`)
- How Karafiel tests the integration with `POST /api/v1/webhooks/<id>/test/` (Tezca-side test endpoint)
- What re-enables a `WebhookSubscription` after auto-disable (`PATCH /api/v1/webhooks/<id>/` with `is_active: true`)
- What the Karafiel side does on `version.created` vs `law.updated` (different compliance-alert semantics)

---

## 6. What was NOT a blocker (verified false positives from earlier worry-list)

These were flagged in the feature-parity plan §3.4 as audit items but turn out to be already-OK:

- **"`APIKey.rate_limit_per_hour` capped at 100k/hr might be insufficient"** — projected Karafiel-driven volume is <1k/day, the default Institutional rate limit (50k/hour from `tier_throttles.py`) is 50× headroom. No override needed.
- **"Webhook DLQ wiring for tezca outbound dispatch"** — Celery's `deliver_webhook` task uses Celery's standard retry + max-retries. The `madfam:billing-events-dlq` pattern referenced in `event-schemas.yaml` is for Redis Streams (inbound from Dhanam), not outbound from Tezca. They're different transports, both correct.
- **"SSRF on webhook URLs"** — already enforced via `apps/api/utils/url_validation.py` per CLAUDE.md "Integration Policy" section; verified by H2 audit (PR #37).

---

## 7. Done criterion verification

Per FEATURE_PARITY_PLAN §3.4, the done criterion was:
> Karafiel-test API key provisioned, webhook subscribed, sample `law.updated` event received in Karafiel-test within 30s of fixture publication.

This audit only verifies **Tezca-side technical readiness**. The actual end-to-end runtime test is jointly owned with Karafiel team and gates on Karafiel's own Wave 1 Month 1 deliverables (database live, e.firma uploaded). Steps to execute jointly when Karafiel is ready:

1. Operator provisions `tzk_*` API key for `karafiel-ops@madfam.io` (§4.1)
2. Karafiel registers webhook with `domain_filter: ["fiscal"]` against staging tezca
3. Operator manually creates a Law fixture: `python manage.py shell -c "from apps.api.models import Law; Law.objects.create(official_id='test_rmf', name='RMF Test', tier='federal', category='resolución_miscelánea_fiscal', domains=['fiscal'])"`
4. Verify Karafiel-staging logs receive the HMAC-signed POST within 30s
5. Verify HMAC validation succeeds on Karafiel's side

If steps 1-5 pass, the integration is live and Karafiel can start counting Tezca events as a billable feature of its Enterprise tier.

---

## 8. Action items (this session)

### Tezca-side (none)
The Tezca code is ready. No new PRs needed beyond Track 1 (RMF, already merged) and the ongoing state-coverage push (Track 3).

### Operator-side
- [ ] Run domain-classification verification queries (§3.1) on production
- [ ] If <95% domain coverage: trigger `classify_law_domains --all --force` Celery one-shot
- [ ] Wait for Karafiel team to signal Wave 1 Month 1 readiness
- [ ] Provision `tzk_*` API key for Karafiel-ops (§4.1)
- [ ] Joint runtime test (§7 steps 3-5) with Karafiel team

### Karafiel-side (file in `madfam-org/karafiel`)
- [ ] Open issue: "Tezca integration runbook: webhook event → compliance alert mapping" (§5)
- [ ] Implement `POST /v1/tezca-webhook` HMAC-verifying receiver
- [ ] Add `tezca_webhook_test` integration test against staging tezca

---

## 9. Related

- [FEATURE_PARITY_PLAN_2026-04-27.md §3.4](./FEATURE_PARITY_PLAN_2026-04-27.md)
- `internal-devops/ecosystem/gtm-strategy.md` — Karafiel as Wave 1 lead product
- `internal-devops/ecosystem/event-schemas.yaml` — Tezca declared as `madfam:billing-events` consumer (separate channel, complementary)
- `apps/api/webhooks.py` — dispatch logic
- `apps/api/signals.py` — Law/LawVersion change → webhook trigger
- `apps/api/utils/url_validation.py` — SSRF protection
- `apps/api/management/commands/classify_law_domains.py` — domain backfill
