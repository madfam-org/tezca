# Account data egress — `tezca-egress/v1`

Self-service account takeout. A customer can retrieve everything Tezca stores
about them, complete and re-usable, without an operator in the loop.

This closes criterion **C6 (verified egress)** of the self-serve sellable
program.

---

## Endpoints

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/api/v1/user/export/` | The envelope as an inline JSON response |
| `GET` | `/api/v1/user/export/download/` | The same envelope as a `.json` file attachment |

Both are implemented in `apps/api/egress_views.py` and require authentication.

### Authentication

The platform's existing `CombinedAuthentication` applies — either a Janua JWT
(`Authorization: Bearer …`) or a Tezca API key (`X-API-Key: tzk_…`).

```bash
# With a Janua session token
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.tezca.mx/api/v1/user/export/download/" -o tezca-export.json

# With an API key
curl -H "X-API-Key: tzk_your_key" \
  "https://api.tezca.mx/api/v1/user/export/" | jq .
```

### Scoping

The export is keyed on the caller's **Janua subject** (`janua_user_id`). Every
queryset in `_collect()` filters on that key; there is no unfiltered read.

The two authenticated principal shapes resolve differently, and the distinction
matters:

- **Janua JWT** — `request.user.id` is the `sub` claim and *is* the scope key.
- **API key** — `request.user.id` is the synthetic string `"apikey:<prefix>"`,
  which is **not** a Janua subject. The real subject is read off the `APIKey`
  row. A key never linked to an account (`janua_user_id == ""`) has no account
  to export and gets `403` rather than an export under a bogus scope key.

Cross-tenant isolation is proven in `tests/api/test_egress_views.py`
(`TestEgressTenantIsolation`): two fully-populated accounts are seeded and each
caller's response is asserted to contain none of the other's rows, in both
directions, including the indirect paths (webhooks and usage logs, which hang
off API keys rather than off the subject directly).

---

## Envelope

```jsonc
{
  "contract": "tezca-egress/v1",
  "exportedAt": "2026-08-22T18:00:00+00:00",
  "subject": {
    "janua_user_id": "…",
    "requested_via": "janua_jwt",          // or "api_key"
    "requesting_api_key_prefix": ""
  },
  "account": {
    "janua_user_id": "…",
    "emails": ["…"],
    "organizations": ["…"],
    "current_tier": "institutional",
    "active_trial": null,                   // or {tier, started_at, ends_at, …}
    "api_key_count": 2,
    "active_api_key_count": 1
  },
  "preferences": {                          // null when never set
    "bookmarks": [], "recently_viewed": [], "preferences": {},
    "created_at": "…", "updated_at": "…"
  },
  "collections": {
    "api_keys": [],                         // metadata only; secrets are unrecoverable hashes
    "annotations": [],                      // notes and highlights on articles
    "alerts": [],                           // law-change alert subscriptions
    "notifications": [],                    // in-app notifications
    "newsletter_subscriptions": [],
    "feature_interests": [],                // interest-capture submissions
    "webhook_subscriptions": []             // signing secrets redacted
  },
  "usage": {
    "law_exports": { "total": 0, "by_format": {}, "first_at": null, "last_at": null },
    "api_calls":   { "total": 0, "by_endpoint": {}, "api_key_prefixes": [], "first_at": null, "last_at": null }
  },
  "counts": { "annotations": 0, "…": 0 },
  "truncated": [],                          // [{collection, exported, total}] when capped
  "excluded": [ { "what": "law_corpus", "reason": "…" } ]
}
```

### Completeness

`collections` covers every table in `apps/api/models.py` that carries a
`janua_user_id`, plus the two that Tezca keys by API key
(`WebhookSubscription`, `APIUsageLog`) resolved through the caller's own keys.

Collections are capped at `MAX_ROWS_PER_COLLECTION` (10,000). When a cap bites,
the `truncated` array reports the collection's true total — the export never
silently claims to be complete when it is not.

### Usage is summarized, not dumped

`usage` reports aggregates (counts by format, counts by endpoint, first/last
timestamps) rather than raw per-request rows. Raw `APIUsageLog` rows are
operational telemetry containing IP addresses; the customer-meaningful fact is
how much they used and of what.

---

## What is deliberately excluded

The envelope's `excluded` array declares each omission and its reason in-band,
so a reader never has to guess whether an absence is a bug.

| Excluded | Why |
|---|---|
| **`law_corpus`** | Mexican legislation, SCJN jurisprudencia and tesis, and their versions are **public-domain primary sources that Tezca republishes but does not own**. They are not the customer's data. Available from the public API (`/api/v1/laws/`, `/api/v1/judicial/`) or per-law export. |
| `search_analytics` | `SearchQuery` rows are keyed to a hashed session identifier, not to an account. They cannot be attributed to a user, so they are not exportable as that user's data. |
| `api_key_secrets` | Only irreversible hashes are stored. Prefixes and metadata are included; secret values are not recoverable. |
| `webhook_signing_secrets` | Credentials, not content. Presence is reported (`has_secret`); values are redacted. |
| `billing_records` | Invoices, payment methods, and CFDI live in **Dhanam**, the billing system of record. |
| `identity_profile` | Name, email, password, session history live in **Janua**, the identity provider. |

The last two are a deliberate boundary, not a gap: Tezca is not the system of
record for either, and duplicating them here would create a second, staler copy
of regulated data.

---

## Tests

```bash
poetry run pytest tests/api/test_egress_views.py -v
```

20 tests: envelope shape and contract version, completeness across every
collection, entitlement and trial reporting, usage summaries, secret redaction,
declared exclusions, declared truncation, cross-tenant isolation in both
directions (including the indirect webhook and usage-log paths), principal
resolution for both auth shapes, unlinked-key refusal, anonymous refusal, and
the download variant's headers and scoping.
