import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('posthog-js', () => ({
    default: {
        init: vi.fn(),
        identify: vi.fn(),
        reset: vi.fn(),
        capture: vi.fn(),
    },
}));

describe('posthog analytics', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('initPostHog is a no-op when POSTHOG_KEY is not set', async () => {
        const { initPostHog } = await import('@/lib/analytics/posthog');
        // Should not throw
        initPostHog();
    });

    it('identifyUser is a no-op when not initialized', async () => {
        const { identifyUser } = await import('@/lib/analytics/posthog');
        identifyUser('user-1');
    });

    it('resetUser is a no-op when not initialized', async () => {
        const { resetUser } = await import('@/lib/analytics/posthog');
        resetUser();
    });

    it('trackEvent is a no-op when not initialized', async () => {
        const { trackEvent } = await import('@/lib/analytics/posthog');
        trackEvent('page_view', { path: '/' });
    });
});
