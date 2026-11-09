/**
 * Server-render guard for the Janua client config (used by `lib/janua.tsx`).
 *
 * `@janua/typescript-sdk` 0.1.x starts `setInterval(checkAndRefresh, 60_000)`
 * in the `JanuaClient` constructor and never clears it, and `<JanuaProvider>`
 * builds a client in `useState(() => new JanuaClient(config))`, which runs on
 * EVERY server render. Each server-rendered page view therefore left a
 * permanent interval behind whose async context pinned the whole request
 * (~110 KB per view, never collected). That is what OOM-killed tezca-web every
 * 20–46 h (V8 "Ineffective mark-compacts near heap limit", exit 139).
 *
 * Token storage is browser-only, so there is nothing to refresh during SSR and
 * the server copy loses nothing. The browser keeps today's config untouched
 * (same object, so the SDK default or the caller's own `autoRefreshTokens`
 * still applies and signed-in sessions keep refreshing).
 *
 * The SDK fix ships in `@janua/typescript-sdk` 0.1.5; once this app runs on
 * it, this guard can go (the characterisation test in
 * `__tests__/lib/janua-config.test.ts` fails when the SDK stops leaking).
 */
export function serverSafeJanuaConfig<C extends object>(
  config: C,
  isServer: boolean = typeof window === 'undefined',
): C & { autoRefreshTokens?: boolean } {
  return isServer ? { ...config, autoRefreshTokens: false } : config;
}
