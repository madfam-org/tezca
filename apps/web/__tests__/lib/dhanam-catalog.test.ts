import { describe, it, expect, vi } from 'vitest';
import { fetchTezcaPrices, formatMxnCentavos } from '@/lib/dhanam-catalog';

describe('fetchTezcaPrices (Dhanam catalog, owner ruling 2026-10-14)', () => {
    it('reads the monthly MXN price per tier from the public catalog', async () => {
        const fetchImpl = vi.fn(async (_url: string) =>
            new Response(
                JSON.stringify({
                    slug: 'tezca',
                    tiers: [
                        { slug: 'free', prices: {} },
                        { slug: 'essentials', prices: { MXN: { monthly: 19900 } } },
                        { slug: 'academic', prices: { MXN: { monthly: 59900 } } },
                        { slug: 'institutional', prices: { MXN: { monthly: 199900 } } },
                    ],
                }),
                { status: 200 },
            ),
        );
        const prices = await fetchTezcaPrices(fetchImpl as unknown as typeof fetch);
        expect(fetchImpl.mock.calls[0][0]).toBe('https://api.dhan.am/v1/billing/catalog/tezca');
        expect(prices).toEqual({ free: null, essentials: 19900, academic: 59900, institutional: 199900 });
    });

    it('throws when the catalog is unavailable, so no typed price is shown', async () => {
        const fetchImpl = vi.fn(async () => new Response('x', { status: 503 }));
        await expect(fetchTezcaPrices(fetchImpl as unknown as typeof fetch)).rejects.toThrow('503');
    });

    it('formats centavos as whole pesos', () => {
        expect(formatMxnCentavos(19900)).toBe('$199');
        expect(formatMxnCentavos(199900)).toBe('$1,999');
    });
});
