import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('billing', () => {
    const originalEnv = process.env;

    beforeEach(() => {
        vi.resetModules();
    });

    afterEach(() => {
        process.env = originalEnv;
    });

    it('getCheckoutUrl builds a URL with plan and product params', async () => {
        const { getCheckoutUrl } = await import('@/lib/billing');
        const url = getCheckoutUrl('academic');
        expect(url).toContain('plan=tezca_academic');
        expect(url).toContain('product=tezca');
    });

    it('getCheckoutUrl includes user_id and return_url when provided', async () => {
        const { getCheckoutUrl } = await import('@/lib/billing');
        const url = getCheckoutUrl('essentials', 'user-123', 'https://tezca.mx/done');
        expect(url).toContain('user_id=user-123');
        expect(url).toContain('return_url=');
    });

    it('hasPaidAccess returns true for paid tiers', async () => {
        const { hasPaidAccess } = await import('@/lib/billing');
        expect(hasPaidAccess('essentials')).toBe(true);
        expect(hasPaidAccess('academic')).toBe(true);
        expect(hasPaidAccess('institutional')).toBe(true);
        expect(hasPaidAccess('madfam')).toBe(true);
    });

    it('hasPaidAccess returns false for non-paid tiers', async () => {
        const { hasPaidAccess } = await import('@/lib/billing');
        expect(hasPaidAccess('anon')).toBe(false);
        expect(hasPaidAccess('free_member')).toBe(false);
        expect(hasPaidAccess('community')).toBe(false);
        expect(hasPaidAccess(null)).toBe(false);
    });

    it('getTrialCheckoutUrl includes mode=trial_cc', async () => {
        const { getTrialCheckoutUrl } = await import('@/lib/billing');
        const url = getTrialCheckoutUrl('academic');
        expect(url).toContain('mode=trial_cc');
        expect(url).toContain('plan=tezca_academic');
    });

    it('getPromoCheckoutUrl includes _promo suffix in plan', async () => {
        const { getPromoCheckoutUrl } = await import('@/lib/billing');
        const url = getPromoCheckoutUrl('institutional', 'u1');
        expect(url).toContain('plan=tezca_institutional_promo');
        expect(url).toContain('user_id=u1');
    });
});
