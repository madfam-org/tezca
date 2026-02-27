# apps/admin/Dockerfile — Next.js admin console
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

# Install ALL dependencies (unfiltered npm ci installs platform-specific optional deps)
ARG NPM_MADFAM_TOKEN
RUN npm ci

# ── Stage 2: Build ───────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/admin/node_modules ./apps/admin/node_modules

# Copy source code
COPY package.json package-lock.json ./
COPY apps/admin ./apps/admin
COPY packages/ui ./packages/ui
COPY packages/lib ./packages/lib
COPY packages/tsconfig ./packages/tsconfig

# Build args
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY=$NEXT_PUBLIC_JANUA_PUBLISHABLE_KEY

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace=apps/admin

# Verify standalone output exists at expected path
RUN test -f apps/admin/.next/standalone/apps/admin/server.js || \
    (echo "ERROR: server.js not found at expected path" && ls -la apps/admin/.next/standalone/ && exit 1)

# ── Stage 3: Runtime ─────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone build output
COPY --from=builder /app/apps/admin/.next/standalone ./
COPY --from=builder /app/apps/admin/.next/static ./apps/admin/.next/static

USER nextjs

EXPOSE 3001
ENV PORT=3001
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3001/api/health || exit 1

CMD ["node", "apps/admin/server.js"]
