// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderToString } from 'react-dom/server';
import { JanuaProvider } from '@/lib/auth';

const SDK_REFRESH_INTERVAL_MS = 60 * 1000;
const LAYOUT_CONFIG = {
    baseURL: 'https://auth.example.test',
    apiKey: 'pk_test_synthetic',
    autoRefreshTokens: true,
    skipRemoteAuth: true,
};

// Real @janua/nextjs (admin does not stub it here). Server-render the provider
// the root layout renders and assert it leaves no SDK refresh interval behind.
describe('admin JanuaProvider server render', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('renders its children', () => {
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
});

// The guard only works if the root layout renders this wrapper, not the
// package's provider directly.
describe('admin root layout', () => {
    it('renders JanuaProvider from @/lib/auth, never from @janua/nextjs', async () => {
        const { readFileSync } = await import('node:fs');
        const { resolve } = await import('node:path');
        const layout = readFileSync(resolve(__dirname, '../../app/layout.tsx'), 'utf8');
        expect(layout).toMatch(/import\s*\{[^}]*\bJanuaProvider\b[^}]*\}\s*from\s*["']@\/lib\/auth["']/);
        expect(layout).not.toMatch(/from\s*["']@janua\/nextjs["']/);
    });
});
