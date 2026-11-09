// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest';
import { JanuaClient } from '@janua/typescript-sdk';
import { serverSafeJanuaConfig } from '@/lib/janua-config';

const SDK_REFRESH_INTERVAL_MS = 60 * 1000;
// The shape app/layout.tsx passes (synthetic values; admin asks for refresh).
const LAYOUT_CONFIG = {
    baseURL: 'https://auth.example.test',
    apiKey: 'pk_test_synthetic',
    autoRefreshTokens: true,
};

function refreshIntervalsStarted(spy: { mock: { calls: ReadonlyArray<ReadonlyArray<unknown>> } }) {
    return spy.mock.calls.filter(([, ms]) => ms === SDK_REFRESH_INTERVAL_MS).length;
}

describe('serverSafeJanuaConfig (admin)', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('overrides the layout autoRefreshTokens: true on the server', () => {
        expect(serverSafeJanuaConfig(LAYOUT_CONFIG, true)).toEqual({ ...LAYOUT_CONFIG, autoRefreshTokens: false });
        expect(LAYOUT_CONFIG.autoRefreshTokens).toBe(true);
    });

    it('returns the browser config untouched (same object)', () => {
        expect(serverSafeJanuaConfig(LAYOUT_CONFIG, false)).toBe(LAYOUT_CONFIG);
    });

    it('detects the server from the absence of window by default', () => {
        expect(typeof window).toBe('undefined');
        expect(serverSafeJanuaConfig(LAYOUT_CONFIG).autoRefreshTokens).toBe(false);
    });

    it('a JanuaClient built from the server config starts no refresh interval', () => {
        const spy = vi.spyOn(globalThis, 'setInterval');
        for (let i = 0; i < 25; i++) new JanuaClient(serverSafeJanuaConfig(LAYOUT_CONFIG, true));
        expect(refreshIntervalsStarted(spy)).toBe(0);
    });

    // Characterisation of the SDK leak this guard exists for; fails once
    // @janua/typescript-sdk 0.1.5 (no interval off-browser) is installed.
    it('the layout config without the guard starts one interval per client', () => {
        const spy = vi.spyOn(globalThis, 'setInterval');
        spy.mockImplementation((() => 0) as unknown as typeof setInterval);
        new JanuaClient(LAYOUT_CONFIG);
        new JanuaClient(LAYOUT_CONFIG);
        expect(refreshIntervalsStarted(spy)).toBe(2);
    });
});
