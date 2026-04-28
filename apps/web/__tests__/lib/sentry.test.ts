/**
 * Sentry is loaded conditionally — only when NEXT_PUBLIC_SENTRY_DSN is set
 * AND @sentry/nextjs is installable. These tests stub the dynamic import
 * via the `Function('return import("..."))` indirection used in sentry.ts.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('initSentry / captureError — DSN gating', () => {
    beforeEach(() => {
        vi.resetModules();
        // No DSN by default
        delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    });

    afterEach(() => {
        delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    });

    it('initSentry() is a no-op when DSN is unset', async () => {
        const mod = await import('@/lib/sentry');
        // Should not throw; should not crash even without sentry installed
        mod.initSentry();
    });

    it('captureError() is a no-op when DSN is unset', async () => {
        const mod = await import('@/lib/sentry');
        mod.captureError(new Error('boom'));
        mod.captureError(new Error('boom'), { extra: 'info' });
    });
});

describe('captureError — DSN set, Sentry not installed', () => {
    beforeEach(() => {
        vi.resetModules();
        process.env.NEXT_PUBLIC_SENTRY_DSN = 'https://fake@sentry.example.com/1';
    });

    afterEach(() => {
        delete process.env.NEXT_PUBLIC_SENTRY_DSN;
    });

    it('initSentry() swallows the import-failure cleanly when @sentry/nextjs is missing', async () => {
        const mod = await import('@/lib/sentry');
        // The module's loadSentry catches the ImportError and returns null;
        // the .then() hand-off then short-circuits.
        mod.initSentry();
        // Tick: the unresolved promise should not throw.
        await new Promise((r) => setTimeout(r, 10));
    });

    it('captureError() handles missing context (no-context branch)', async () => {
        const mod = await import('@/lib/sentry');
        mod.captureError(new Error('x'));
        await new Promise((r) => setTimeout(r, 10));
    });

    it('captureError() handles a context object (context branch)', async () => {
        const mod = await import('@/lib/sentry');
        mod.captureError(new Error('x'), { userId: 'u1', flow: 'auth' });
        await new Promise((r) => setTimeout(r, 10));
    });
});
