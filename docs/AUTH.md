# Authentication — Janua Integration

Tezca authenticates users through Janua, a self-hosted OIDC provider in the MADFAM ecosystem. This is the most complete Janua integration across MADFAM projects and serves as the reference implementation for other repos.

---

## Architecture

```
Browser
  |
  |  1. OAuth authorize redirect
  v
Janua (OIDC Provider)
  |
  |  2. Authorization code + client secret exchange
  v
Next.js App (SSR)                      Admin App
  |  @janua/nextjs-sdk                   |  Same auth pattern,
  |  (server-side session management)    |  separate client config
  |                                      |
  |  3. API requests with Bearer token   |
  v                                      v
Backend API (JWT validation)
```

Tezca uses `@janua/nextjs-sdk` for server-side authentication in the Next.js App Router. The SDK handles the full OAuth flow, session management, and token refresh on the server side. The backend API independently validates JWTs for all API requests.

The admin app uses the same authentication pattern with a separate OAuth client configuration.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `JANUA_CLIENT_ID` | OAuth client ID for the Tezca application, registered in Janua. |
| `JANUA_CLIENT_SECRET` | OAuth client secret. Tezca uses a confidential client, so this value is required and must be kept secret. |
| `JANUA_ISSUER_URL` | The Janua API base URL. Production: `https://api.janua.dev`. |
| `JANUA_AUDIENCE` | The expected audience claim: `tezca-api`. |

These variables must be set in the server environment (`.env.local` for development, deployment secrets for production). Do not expose `JANUA_CLIENT_SECRET` to the browser.

---

## OAuth Client Registration

Register an OAuth client in the Janua dashboard with the following settings:

| Field | Value |
|-------|-------|
| Application Name | Tezca |
| Client Type | Confidential |
| Audience | `tezca-api` |
| Redirect URI | `https://tezca.dev/api/auth/callback/janua` |
| Grant Type | Authorization Code |

For the admin app, register a separate OAuth client with its own client ID, secret, and redirect URI.

---

## Audience Validation

Every JWT issued by Janua contains an `aud` (audience) claim. Tezca's backend rejects tokens where the `aud` claim does not match `tezca-api`.

This prevents cross-application token reuse. A token issued for a different MADFAM service (e.g., `stratum-tcg-api` or `yantra4d-api`) cannot be used to access Tezca's API, even though all tokens are signed by the same Janua instance.

The audience value must be consistent across:

1. The `JANUA_AUDIENCE` environment variable in Tezca.
2. The audience field in the Janua OAuth client registration.
3. The audience parameter included in the authorization request by the SDK.

---

## Tier-Based Authorization

After authentication, every request gets a tier that controls feature access and rate limits. Tiers are managed by Dhanam (billing) and embedded as JWT claims by Janua.

### Tier Hierarchy

| Tier | Rank | Description |
|------|------|-------------|
| `anon` | 0 | Unauthenticated requests. Most restrictive limits. |
| `essentials` | 1 | Free tier (default for authenticated users). Matches the open-source self-hosted build. |
| `pro` | 2 | Paid tier. Unlocks search analytics, API keys, bulk download, premium exports. |
| `madfam` | 3 | Internal/operator tier. All features enabled, no limits. |

Legacy tier names are normalized automatically: `free` maps to `essentials`, `premium` maps to `pro`, `internal` and `enterprise` map to `madfam`.

### JWT Claim Extraction

`CombinedAuthentication` reads the tier from JWT claims in this order:

1. `tezca_tier` -- product-specific claim set by Dhanam via Janua webhook. Preferred.
2. `tier` -- generic cross-product claim.
3. `plan` -- legacy claim name.
4. Falls back to `"free"` if none are present.

The product-specific `tezca_tier` claim allows a user to have different tiers across MADFAM products (e.g., `pro` on Tezca but `essentials` on Yantra4D).

### Feature Gating

Use `RequireTier` as a DRF permission class to gate endpoints:

```python
from apps.api.middleware.tier_permissions import RequireTier

@permission_classes([RequireTier.of("pro")])
def premium_endpoint(request):
    ...
```

Only `pro` and above features are gated. Essentials-level features are identical to the open-source self-hosted build and require no permission check beyond authentication.

For individual feature flags, use `check_feature()`:

```python
from apps.api.middleware.tier_permissions import check_feature

if check_feature(request.user.tier, "search_analytics"):
    ...
```

Feature definitions and per-tier limits are in `apps/api/tiers.json`.

### Rate Limiting by Tier

Tier limits from `tiers.json` control request quotas:

| Tier | API requests/day | Search results/query |
|------|-----------------|---------------------|
| `essentials` | 500 | 25 |
| `pro` | Unlimited (-1) | Unlimited (-1) |
| `madfam` | Unlimited (-1) | Unlimited (-1) |

Use `get_tier_limits(tier)` to retrieve the full limits dict for rate limiter configuration.

---

## Admin App

The admin interface uses the same Janua authentication mechanism but with a separate OAuth client configuration. This separation allows:

- Different redirect URIs for the admin domain.
- Independent client secret rotation without affecting the main application.
- Distinct access control policies if needed.

The admin app's environment variables follow the same naming convention (`JANUA_CLIENT_ID`, `JANUA_CLIENT_SECRET`, etc.) but are set to the admin-specific OAuth client values.

---

## Reference Implementation

Tezca is the most complete Janua integration in the MADFAM ecosystem. When implementing Janua auth in a new project, use this repo as a reference for:

- **Next.js SSR auth flow**: Server-side token exchange and session management with `@janua/nextjs-sdk`.
- **Confidential client pattern**: Secure client secret handling on the server, never exposed to the browser.
- **Audience isolation**: Per-application audience claims preventing cross-app token reuse.
- **Admin separation**: Independent auth configuration for admin interfaces.

Other MADFAM repos with Janua integrations (for comparison):

| Repo | Stack | Auth Pattern |
|------|-------|--------------|
| Stratum-TCG | FastAPI + React | JWKS validation, public client with PKCE |
| Yantra4D | Flask + Vite | Middleware decorators, role/tier enforcement |
| Tezca | Next.js | SSR confidential client (this repo) |

---

## Troubleshooting

### 401 Unauthorized on API requests

**Possible causes**:

- **Audience mismatch**: The token's `aud` claim does not match `tezca-api`. Verify the OAuth client registration in Janua.
- **Expired token**: The access token has expired and the SDK failed to refresh it. Check server logs for refresh errors.
- **Missing Authorization header**: The request did not include a Bearer token. Verify the SDK is attaching tokens to API requests.

### OAuth callback errors

**Symptom**: Redirect to `/api/auth/callback/janua` fails with an error page.

**Possible causes**:

- **Redirect URI mismatch**: The callback URL does not match what is registered in Janua. The value must be exact, including protocol, domain, and path.
- **Invalid client secret**: `JANUA_CLIENT_SECRET` is incorrect or has been rotated without updating the Tezca environment.
- **Janua unreachable**: The server cannot reach `JANUA_ISSUER_URL` to exchange the authorization code.

### Cross-app token reuse rejected

**Symptom**: A user authenticated in another MADFAM app receives a 401 when calling Tezca's API.

**Cause**: This is expected behavior. Audience validation ensures tokens are scoped to a single application. The user must authenticate through Tezca's own OAuth flow.

### Admin app authentication fails independently

**Symptom**: The main app works but the admin app returns auth errors.

**Cause**: The admin app uses a separate OAuth client. Check that the admin-specific `JANUA_CLIENT_ID` and `JANUA_CLIENT_SECRET` are set correctly in the admin app's environment.

### Session lost after deployment

**Symptom**: Users are logged out after a deployment.

**Cause**: Server-side sessions may be stored in memory or in a store that was cleared during deployment.

**Fix**: Verify the session store configuration. Use a persistent store (e.g., Redis) for production deployments to preserve sessions across restarts.

### 403 Forbidden on tier-gated endpoints

**Symptom**: Authenticated user gets a 403 with a message about upgrading their tier.

**Cause**: The user's tier (from JWT claims) does not meet the endpoint's minimum tier requirement. The response body includes an upgrade URL.

**Fix**: Verify the user's subscription status in Dhanam. Check that Janua is issuing the correct `tezca_tier` claim. If the user recently upgraded, they may need to re-authenticate to get a fresh token with the updated claim.
