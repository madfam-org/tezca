# apps/web/Dockerfile — Next.js public portal
# Build context: project root (monorepo)

# ── Stage 1: Dependencies ────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app

# Copy workspace root package files
COPY package.json package-lock.json .npmrc ./

# Copy ALL workspace package.json files for full dependency resolution
# (npm ci --workspace=... skips platform-specific optional deps — npm/cli#4828)
COPY apps/admin/package.json apps/admin/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/lib/package.json packages/lib/package.json
COPY packages/tsconfig/package.json packages/tsconfig/package.json
COPY packages/api-client/package.json packages/api-client/package.json

# Install dependencies
ARG NPM_MADFAM_TOKEN
RUN npm ci

# Explicitly install musl-compatible native bindings for Alpine
# npm ci skips platform-specific optional deps in Buildx (npm/cli#4828)
RUN npm install --no-save \
    lightningcss-linux-x64-musl \
    @tailwindcss/oxide-linux-x64-musl \
    @rollup/rollup-linux-x64-musl \
    @unrs/resolver-binding-linux-x64-musl \
    2>/dev/null || true

# ── Stage 2: Build ───────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules

# Copy source code
COPY package.json package-lock.json ./
COPY apps/web ./apps/web
COPY packages/ui ./packages/ui
COPY packages/lib ./packages/lib
COPY packages/tsconfig ./packages/tsconfig

# Build args injected at build time
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_URL
ARG NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_AUTH_URL=$NEXT_PUBLIC_AUTH_URL
ENV NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY=$NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY

# Enable Next.js standalone output for smaller images
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace=apps/web

# Verify standalone output exists at expected path
RUN test -f apps/web/.next/standalone/apps/web/server.js || \
    (echo "ERROR: server.js not found at expected path" && ls -la apps/web/.next/standalone/ && exit 1)

# ── Stage 3: Runtime ─────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone build output
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "apps/web/server.js"]
