# Load Tests

k6 load tests for the Tezca API.

## Prerequisites

Install k6: https://k6.io/docs/get-started/installation/

```bash
# macOS
brew install k6

# Docker alternative
docker run --rm -i grafana/k6 run - <tests/load/search.js
```

## Running

```bash
# Search endpoint — ramps 10→50→100 VUs over 3 min
k6 run tests/load/search.js

# Browse endpoints — law list, detail, articles
k6 run tests/load/browse.js

# Against a deployed environment
k6 run tests/load/search.js --env BASE_URL=https://api.tezca.mx/api/v1
```

## Expected Baselines

| Endpoint | p95 Threshold | Notes |
|----------|---------------|-------|
| `GET /search/` | < 500ms | Full-text search with facets |
| `GET /laws/` | < 300ms | Paginated law list (DB query) |
| `GET /laws/{id}/` | < 200ms | Single law detail |
| `GET /laws/{id}/articles/` | < 500ms | All articles from ES |

## Interpreting Results

- **http_req_duration**: Response time percentiles (p50, p95, p99)
- **http_req_failed**: Error rate (target: < 1%)
- **iterations**: Total completed virtual user iterations
- **vus**: Concurrent virtual users at each point

If thresholds fail, investigate:
1. ES query performance (slow queries log)
2. DB connection pooling
3. Network latency between services
