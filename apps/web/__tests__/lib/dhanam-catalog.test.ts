import { describe, it, expect, vi } from 'vitest';
import {
    catalogDisplayPrice,
    fetchTezcaPrices,
    formatMxnCentavos,
    ivaLabel,
    priceUnitLabel,
} from '@/lib/dhanam-catalog';

// Essentials as Dhanam's catalog lists it: net MXN 199 in `prices`, and the
// MXN 231 its checkout charges in `grossPrices` (rule ceil_whole_peso_iva,
// owned by Dhanam).
const NET = 19900;
const GROSS = 23100;

describe('fetchTezcaPrices (Dhanam catalog, owner ruling 2026-10-14)', () => {
    it('reads the monthly MXN net per tier, marked as before IVA, while there is no grossPrices', async () => {
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
        expect(prices).toEqual({
            free: null,
            essentials: { amount: 19900, ivaIncluded: false },
            academic: { amount: 59900, ivaIncluded: false },
            institutional: { amount: 199900, ivaIncluded: false },
        });
    });

    it('reads grossPrices, IVA included, when the catalog sends it', async () => {
        const fetchImpl = vi.fn(async (_url: string) =>
            new Response(
                JSON.stringify({
                    slug: 'tezca',
                    tiers: [
                        { slug: 'free', prices: {}, grossPrices: {} },
                        {
                            slug: 'essentials',
                            prices: { MXN: { monthly: NET, yearly: null } },
                            grossPrices: {
                                MXN: { monthly: GROSS, yearly: null, ivaRate: 0.16, pricingRule: 'ceil_whole_peso_iva' },
                            },
                        },
                    ],
                }),
                { status: 200 },
            ),
        );
        const prices = await fetchTezcaPrices(fetchImpl as unknown as typeof fetch);
        expect(prices).toEqual({ free: null, essentials: { amount: GROSS, ivaIncluded: true } });
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

describe('catalogDisplayPrice', () => {
    it('falls back to the net when the gross for that interval is null', () => {
        const tier = { prices: { MXN: { monthly: NET } }, grossPrices: { MXN: { monthly: null } } };
        expect(catalogDisplayPrice(tier, 'monthly')).toEqual({ amount: NET, ivaIncluded: false });
    });

    it('never computes a gross from the net (the rounding rule stays in Dhanam)', () => {
        const tier = { prices: { MXN: { monthly: NET } }, grossPrices: {} };
        expect(catalogDisplayPrice(tier, 'monthly')?.amount).toBe(NET);
    });

    it('ignores a gross below the net (wrong unit or field)', () => {
        const tier = { prices: { MXN: { monthly: NET } }, grossPrices: { MXN: { monthly: 231 } } };
        expect(catalogDisplayPrice(tier, 'monthly')).toEqual({ amount: NET, ivaIncluded: false });
    });

    it('returns null for free, unpriced and USD-only tiers', () => {
        expect(catalogDisplayPrice({ prices: {}, grossPrices: {} }, 'monthly')).toBeNull();
        expect(catalogDisplayPrice({ prices: { USD: { monthly: 1999 } }, grossPrices: {} }, 'monthly')).toBeNull();
        expect(catalogDisplayPrice(undefined, 'monthly')).toBeNull();
    });
});

describe('IVA labels', () => {
    it('labels the gross "IVA incluido" and the net "+ IVA" (en: VAT; nah: the Spanish term)', () => {
        const gross = { amount: GROSS, ivaIncluded: true };
        const net = { amount: NET, ivaIncluded: false };
        expect(ivaLabel(gross, 'es')).toBe('IVA incluido');
        expect(ivaLabel(net, 'es')).toBe('+ IVA');
        expect(ivaLabel(gross, 'en')).toBe('VAT included');
        expect(ivaLabel(net, 'en')).toBe('+ VAT');
        expect(ivaLabel(net, 'nah')).toBe('+ IVA');
        expect(priceUnitLabel('MXN/mes', gross, 'es')).toBe('MXN/mes, IVA incluido');
        expect(priceUnitLabel('MXN/mo', net, 'en')).toBe('MXN/mo + VAT');
    });
});
