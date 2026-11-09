// @vitest-environment node
import { createRequire } from 'node:module';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderToString } from 'react-dom/server';
import { JanuaProvider } from '@/lib/janua';

// vitest.config.mts aliases `@janua/nextjs` to a pass-through stub. This test
// needs the REAL provider (it is the one that builds a JanuaClient per render),
// so load the installed package's ESM build by file path (its CJS build pulls
// the SDK's CJS file, which Node refuses to load as CommonJS).
vi.mock('@janua/nextjs', async () => {
  const cjsEntry = createRequire(import.meta.url).resolve('@janua/nextjs');
  return import(/* @vite-ignore */ cjsEntry.replace(/index\.js$/, 'index.mjs'));
});

const SDK_REFRESH_INTERVAL_MS = 60 * 1000;
// The same shape app/layout.tsx passes (synthetic values).
const LAYOUT_CONFIG = { baseURL: 'https://auth.example.test', apiKey: 'pk_test_synthetic' };

// Server-render the provider the root layout renders on every page view and
// assert it leaves no SDK refresh interval behind. Before the fix each render
// started a 60 s setInterval that pinned the request until the pod OOM'd.
describe('JanuaProvider server render', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders its children with the real @janua/nextjs provider', () => {
    const html = renderToString(
      <JanuaProvider config={LAYOUT_CONFIG}>
        <p>child</p>
      </JanuaProvider>,
    );
    expect(html).toContain('child');
  });

  it('starts no refresh interval across 20 server renders', () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    for (let i = 0; i < 20; i++) {
      renderToString(
        <JanuaProvider config={LAYOUT_CONFIG}>
          <p>page {i}</p>
        </JanuaProvider>,
      );
    }
    expect(spy.mock.calls.filter(([, ms]) => ms === SDK_REFRESH_INTERVAL_MS)).toHaveLength(0);
  });

  it('starts no refresh interval even when the layout asks for auto-refresh', () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    for (let i = 0; i < 5; i++) {
      renderToString(
        <JanuaProvider config={{ ...LAYOUT_CONFIG, autoRefreshTokens: true }}>
          <p>page {i}</p>
        </JanuaProvider>,
      );
    }
    expect(spy.mock.calls.filter(([, ms]) => ms === SDK_REFRESH_INTERVAL_MS)).toHaveLength(0);
  });
});

// The guard only works if the root layout renders this wrapper, not the
// package's provider directly.
describe('root layout', () => {
  it('renders JanuaProvider from @/lib/janua, never from @janua/nextjs', async () => {
    const { readFileSync } = await import('node:fs');
    const { resolve } = await import('node:path');
    const layout = readFileSync(resolve(__dirname, '../../app/layout.tsx'), 'utf8');
    expect(layout).toMatch(/import\s*\{\s*JanuaProvider\s*\}\s*from\s*["']@\/lib\/janua["']/);
    expect(layout).not.toMatch(/from\s*["']@janua\/nextjs["']/);
  });
});
