# @tezca/api-client

TypeScript SDK for the Tezca API -- Mexico's open law platform.

## Installation

```bash
npm install @tezca/api-client --registry https://npm.madfam.io
```

## Quick Start

```typescript
import { TezcaClient } from "@tezca/api-client";

// API key auth (for programmatic access)
const tezca = new TezcaClient({ apiKey: "tzk_..." });

// JWT auth (for user-specific endpoints)
const tezca = new TezcaClient({ token: "eyJ..." });

// List laws
const laws = await tezca.laws.list({ domain: "finance" });

// Full-text search
const results = await tezca.search("impuesto sobre la renta");

// Get a specific law
const law = await tezca.laws.get("ley-federal-del-trabajo");

// Get articles
const articles = await tezca.laws.articles("ley-federal-del-trabajo");
```

## API Reference

### `new TezcaClient(config)`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `apiKey` | `string?` | -- | API key with `tzk_` prefix |
| `token` | `string?` | -- | Janua JWT token |
| `baseUrl` | `string` | `https://tezca.mx/api/v1` | API base URL |
| `timeout` | `number` | `30000` | Request timeout in ms |

At least one of `apiKey` or `token` is required.

### Laws

```typescript
tezca.laws.list(params?)       // Paginated law list with filters
tezca.laws.get(lawId)          // Full law detail
tezca.laws.articles(lawId)     // Law articles
tezca.laws.search(lawId, q)    // Search within a law
tezca.laws.related(lawId)      // Related laws
tezca.laws.structure(lawId)    // Hierarchical structure
tezca.laws.references(lawId)   // Cross-references from a law
```

### Search

```typescript
tezca.search(query, params?)  // Full-text search across all articles
tezca.suggest(query)          // Autocomplete suggestions
```

### Categories & Coverage

```typescript
tezca.categories.list()               // Law categories with counts
tezca.categories.states()             // States with laws
tezca.categories.municipalities(state?) // Municipalities (optionally by state)
tezca.coverage.get()                  // Platform coverage statistics
```

### Graph

```typescript
tezca.graph.ego(lawId, params?)    // Ego graph for a law
tezca.graph.overview(params?)      // Global graph overview
tezca.graph.showcase()             // Public showcase (top 50 nodes)
```

### Judicial Records

```typescript
tezca.judicial.search(params)  // Search jurisprudencia and tesis aisladas
tezca.judicial.stats()         // Counts by tipo, materia, epoca
```

### Cross-References

```typescript
tezca.references.forLaw(lawId)             // All refs from a law
tezca.references.batch(lawId, articleIds)  // Batch refs (chunks at 200 IDs)
```

### Bulk Data

```typescript
tezca.bulk.articlePage(params?)  // Single page of bulk articles
tezca.bulk.articles(params?)     // Auto-paginating async iterator

// Stream all articles
for await (const batch of tezca.bulk.articles({ domain: "finance" })) {
  await processBatch(batch);
}
```

### Export

```typescript
tezca.export.download(lawId, format)  // Download law (txt, pdf, latex, docx, epub, json)
tezca.export.quota(lawId)             // Check export quota
```

### Webhooks

```typescript
tezca.webhooks.create({ url, events })  // Subscribe to events
tezca.webhooks.list()                   // List subscriptions
tezca.webhooks.delete(id)               // Remove subscription
tezca.webhooks.test(id)                 // Send test event
```

### User (JWT auth only)

```typescript
tezca.user.preferences()              // Get preferences, bookmarks, recently viewed
tezca.user.addBookmark(lawId)          // Add bookmark
tezca.user.removeBookmark(lawId)       // Remove bookmark
tezca.user.recordView(lawId)           // Record a view

// Annotations
tezca.user.annotations.list(lawId?)    // List annotations
tezca.user.annotations.create(params)  // Create annotation
tezca.user.annotations.update(id, text) // Update text
tezca.user.annotations.delete(id)      // Delete

// Alerts
tezca.user.alerts.list()               // List alert subscriptions
tezca.user.alerts.create(params)       // Create alert
tezca.user.alerts.delete(id)           // Delete alert

// Notifications
tezca.user.notifications.list()        // List notifications
tezca.user.notifications.markRead(ids?) // Mark as read
```

### Changelog

```typescript
tezca.changelog({ since: "2026-01-01", domain: "finance" })
```

## Error Handling

```typescript
import { TezcaAPIError, AuthError, RateLimitError } from "@tezca/api-client";

try {
  await tezca.laws.list();
} catch (err) {
  if (err instanceof RateLimitError) {
    console.log(`Retry after ${err.retryAfter}s`);
  } else if (err instanceof AuthError) {
    console.log("Invalid API key");
  }
}
```

## Publishing

This package is published to `npm.madfam.io` via tag-triggered CI:

```bash
git tag api-client-v0.2.0
git push origin api-client-v0.2.0
```

Requires `NPM_MADFAM_TOKEN` secret in GitHub Actions.

## License

AGPL-3.0
