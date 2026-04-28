# Selva Onboarding Request — `tezca` namespace

**Last Updated:** 2026-04-27
**Track:** Track 8 (cross-cutting) of [FEATURE_PARITY_PLAN_2026-04-27](./FEATURE_PARITY_PLAN_2026-04-27.md) §3.1.
**Status:** Operator action required. Engineering side (Track 2) is already merged behind feature flag `CHAT_ENABLED=false`.
**Audience:** Operator + Selva team (`madfam-org/autoswarm-office`, post-cutover `madfam-org/selva-office`).

---

## Why this ticket exists

Track 2 (`/preguntar` chat scaffold) merged in `ea46ad4` (#47) with a `MockSelvaClient` so it can run in tests + dev without a real Selva connection. To **flip `CHAT_BACKEND=selva` in production**, Selva must provision Tezca as a credentialed `/v1` caller. This is the only remaining blocker to making `/preguntar` live for `essentials+` customers.

Per the MADFAM ECOSYSTEM convention (`internal-devops/ECOSYSTEM.md`):
> Every LLM call should route through Selva (`selva-office`, formerly `autoswarm-office`) at `/v1` (OpenAI-compatible). Do not talk directly to OpenAI / Anthropic from service code.

Tezca holds **zero** OpenAI/Anthropic API keys today and that constraint must hold post-flip.

---

## What Selva needs to provision

### 1. Janua client for the tezca service account

Tezca calls Selva via Janua-relayed bearer tokens (same pattern as every other inter-service call in the ecosystem).

- Create Janua client in `seed_core_clients.py` analogue: `tezca-selva-relay`
- Scope: `selva.chat.completions:invoke`
- Audience: `selva-api`
- Tezca's deployed `tezca-api` already validates Janua JWTs via JWKS at `auth.madfam.io/.well-known/jwks.json`; obtaining a token to call Selva is the new piece.

### 2. Tezca whitelisted on Selva's API

Selva-side authorization config should accept calls from the `tezca-selva-relay` Janua client. Default rate limits + agent-hour metering apply per the live Tulana-validated SKU (`scripts/seed-mvp.py:188-197`):

| Pack | MXN/agent-hour | Use case |
|---|---|---|
| Maker | 85 | Dev / staging |
| Studio | 170 | Production at low scale |
| Enterprise | 255 | High-volume institutional buyers |

Tezca's expected initial volume (rough order-of-magnitude):

- Wave 1 (Karafiel-only): <100 chat completions/day → **Maker pack**
- Wave 2 (essentials+ external customers, post-monetization flip): <1,000/day → **Studio pack**
- Wave 3 (institutional buyers using chat heavily): TBD → re-evaluate

### 3. Default model recommendation

Tezca defaults to `claude-haiku-4-5` (cheapest model that fits ~3K-token RAG context). Selva's model routing should accept this passthrough. Fallback model: `gpt-4o-mini` if Anthropic is rate-limited.

---

## What Tezca-side needs after Selva provisions

The work is small — the Track 2 PR already wired everything. Once Selva confirms readiness:

### Operator (in production env via Enclii)

```bash
# Set the Selva endpoint env vars on the tezca-api Deployment
enclii secrets set \
  SELVA_API_URL="https://selva.town/v1" \
  SELVA_API_TOKEN="<janua-relayed-token>" \
  CHAT_BACKEND="selva" \
  CHAT_ENABLED="true" \
  --service tezca-api --secret

enclii deploy --env production --service tezca-api
```

(`selva.town` is the canonical public Selva domain per RFC 0010 Layer 2; `SELVA_API_URL=https://selva.town/v1`.)

### Smoke test (post-deploy)

```bash
# Manual sanity check using a known essentials API key
curl -X POST https://api.tezca.mx/api/v1/chat/preguntar/ \
  -H "X-API-Key: tzk_..." \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Qué dice el Artículo 31 de la Constitución?"}'

# Expected: 200 OK with {"answer": "...", "citations": [...], "usage": {...}}
# 'model' in usage should be the Selva-resolved real model name, not "mock-model"
```

---

## Context for the Selva team

**What Tezca is using Selva for:** RAG over the Tezca legal corpus. User asks a Spanish-language question, Tezca retrieves top-5 relevant articles via BM25 from Elasticsearch, builds a system prompt with the article snippets + citation rules, sends to Selva, returns the cited answer to the user.

**Token budget per call:**
- System prompt with 5 article snippets × 800 chars: ~4,000 chars (~1,000 tokens)
- User question: ~500 chars (~125 tokens)
- Completion limit: 1,024 tokens
- **Per-call worst case: ~2,200 tokens**

**Per-day caps enforced by Tezca:**
- `essentials`: 30 messages/day
- `academic`: 100 messages/day
- `institutional`: 1,000 messages/day
- `madfam`: unlimited

So **upper bound on tokens shipped to Selva from Tezca: ~2.2M tokens/day** at full institutional volume across all customers. Maker pack ($85/agent-hour) at typical Anthropic Haiku throughput (~50K tokens/sec) would cover this in <1 minute of agent-time, so the metering is comfortable.

**Failure modes Tezca handles gracefully:**
- Selva 5xx → Tezca returns 502 to the user, no charge
- Selva timeout (>30s) → 502
- Selva unauthorized (401) → 502 + log error (config drift)
- ES retrieval failure → empty context, polite reply, no Selva call

Tezca **does not** retry Selva calls. One-shot per user message.

---

## Reference: how Tezca's chat module is wired

```
apps/api/chat/
├── __init__.py
├── selva_client.py       SelvaClient + MockSelvaClient + get_selva_client()
├── retriever.py          BM25 over articles ES index, builds system prompt
└── views.py              POST /api/v1/chat/preguntar/ (4 gating layers)

tests/api/test_chat.py    19 network-free tests (mock client + endpoint)
```

The `get_selva_client()` factory honors `CHAT_BACKEND` env. Production flip:

```python
# apps/api/chat/selva_client.py — already merged
backend = os.getenv("CHAT_BACKEND", "mock").lower()
if backend == "selva":
    return SelvaClient(
        base_url=os.getenv("SELVA_API_URL"),
        token=os.getenv("SELVA_API_TOKEN"),
        default_model=os.getenv("SELVA_DEFAULT_MODEL", "claude-haiku-4-5"),
    )
return MockSelvaClient()
```

If Selva env vars are missing despite `CHAT_BACKEND=selva`, the factory falls back to `MockSelvaClient` and logs an error — failing safe rather than crashing on startup.

---

## Acceptance / done criterion for this ticket

- [ ] Selva provisions Janua client `tezca-selva-relay`
- [ ] Selva whitelists tezca-api as a `/v1/chat/completions` caller
- [ ] Operator sets `SELVA_API_URL`, `SELVA_API_TOKEN`, `CHAT_BACKEND=selva`, `CHAT_ENABLED=true` in tezca-api production env
- [ ] Smoke-test curl returns a real (non-mock) cited answer
- [ ] Selva metering shows tezca calls in operator dashboard
- [ ] Operator updates `CLAUDE.md` "Known Issues" section to remove this as an open item

---

## Related

- [FEATURE_PARITY_PLAN_2026-04-27.md §3.1](./FEATURE_PARITY_PLAN_2026-04-27.md)
- `internal-devops/ECOSYSTEM.md` — "Inference: every LLM call should route through Selva"
- `internal-devops/rfcs/0010-autoswarm-to-selva-identity-cutover.md` — namespace/domain cutover
- `apps/api/chat/selva_client.py` — Tezca-side client (already merged in #47)
- `.env.example` — Selva env var documentation
