# Tulana integration boundary

Date: 2026-05-29

Status: active boundary decision

## Direct surfaces

| Surface | URL |
| --- | --- |
| Tezca public product | `https://tezca.mx` |
| Tulana app | `https://tulana-app.madfam.io` |
| Tulana Tezca boundary doc | `../..` from Tulana: `tulana/docs/tulana-tezca-integration-boundaries-2026-05-28.md` |

## Decision

Tezca is not Tulana's legal approval workflow. Tezca should not be named in
Tulana UI/UX as if it approves capture targets, clears legal flags, or blocks
pricing recommendations.

The Tulana UI should remove Tezca wording from legal/capture states unless a
real Tezca workflow is implemented, authenticated, and linked.

## Valid Tezca/Tulana integration points

| Integration | Direction | Rationale |
| --- | --- | --- |
| Tezca as SKU | Tulana evaluates Tezca | Tezca has its own commercial SKU family and benchmark universe |
| Pricing/PMF feedback | Tulana -> Tezca | Tezca product strategy can consume Tulana pricing and WTP outputs |
| Legal-corpus product evidence | Tezca -> Tulana | Future Tezca corpus/completeness metrics can support Tezca SKU claims |
| Compliance/event products | Tezca -> sibling services | Karafiel and other services may consume Tezca legal data APIs |
| Campaign evidence | Tulana/Selva/Phynd CRM -> Tezca | Campaign outcomes can inform Tezca readiness and positioning |

## Invalid integration points

Tezca must not be presented as:

- legal counsel;
- a legal approval engine for Tulana crawler targets;
- the owner of `legal_needs_review` tags;
- the blocker for competitor-price capture;
- a required dependency for non-Tezca SKU recommendation computation.

## Replacement vocabulary for Tulana

| Old implication | Replacement |
| --- | --- |
| `Tezca legal review` | `policy review` or `capture review` |
| `Tezca blocker` | `capture blocked` plus reason |
| `legal_needs_review` in user-facing copy | `review pending`, `approved`, `waived`, `blocked`, or `stale evidence` |
| `Tezca approved` | `operator approved` or `policy approved`, if true |

## What Tezca should expose later

If a real integration becomes valuable, Tezca should expose product evidence,
not approval magic:

- corpus coverage by jurisdiction and legal domain;
- freshness of legal sources;
- API uptime and latency;
- subscription tier metadata from Dhanam;
- usage or buyer-signal events approved for internal analytics;
- legal-data source provenance for Tezca's own SKU claims.

## Implementation notes

- Tulana owns the UI copy removal.
- Tezca owns this boundary doc and any future Tezca-side API/product evidence.
- Selva and Phynd CRM must not write campaign copy implying Tezca approved
  legal claims unless a future signed approval workflow exists.
- Future integration proposals should land as a dated strategy doc and should
  identify the exact API, auth model, owner, and user-facing claim it enables.
