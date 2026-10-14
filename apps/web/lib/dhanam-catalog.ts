'use client';

// Tezca's prices come from Dhanam's public catalog: the amounts Dhanam's
// checkout charges (owner rulings G1-1 and 2026-10-14). Pages render these
// instead of typed figures, and a failed read never falls back to a number.
//
// The catalog lists each tier's MXN prices before IVA in `prices.MXN` and the
// IVA-inclusive amounts the checkout charges in the sibling `grossPrices.MXN`,
// rounded by a rule that lives in Dhanam (`ceil_whole_peso_iva`). Mexican
// consumer law (LFPC Art. 7 Bis) asks for the total price, taxes included, so
// pages show the gross labelled "IVA incluido" and, while the catalog has no
// `grossPrices`, the net labelled "+ IVA", never a bare net figure. The gross
// is never computed here: the rounding rule stays in Dhanam.
import { useEffect, useState } from 'react';

const DHANAM_API_URL = process.env.NEXT_PUBLIC_DHANAM_API_URL || 'https://api.dhan.am';

export type CatalogPeriod = 'monthly' | 'yearly';

/** An amount to display, in MXN centavos. `ivaIncluded` false: the net, shown with "+ IVA". */
export interface DisplayPrice {
    amount: number;
    ivaIncluded: boolean;
}

/** Monthly display price per catalog tier slug; null when unpriced. */
export type TezcaPrices = Record<string, DisplayPrice | null>;

function asAmount(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null;
}

/** The `MXN` entry of a `prices` or `grossPrices` block, if any. */
function mxnBlock(block: unknown): Record<string, unknown> | null {
    if (!block || typeof block !== 'object') return null;
    const mxn = (block as Record<string, unknown>).MXN;
    return mxn && typeof mxn === 'object' ? (mxn as Record<string, unknown>) : null;
}

/** Pick the amount to show for one period of a catalog tier. */
export function catalogDisplayPrice(tier: unknown, period: CatalogPeriod): DisplayPrice | null {
    if (!tier || typeof tier !== 'object') return null;
    const { prices, grossPrices } = tier as { prices?: unknown; grossPrices?: unknown };
    const net = asAmount(mxnBlock(prices)?.[period]);
    const gross = asAmount(mxnBlock(grossPrices)?.[period]);
    // A gross below the net is not a gross (wrong unit or field): show the net.
    if (gross !== null && (net === null || gross >= net)) return { amount: gross, ivaIncluded: true };
    if (net !== null) return { amount: net, ivaIncluded: false };
    return null;
}

const IVA_LABELS = {
    es: { included: 'IVA incluido', plus: '+ IVA' },
    en: { included: 'VAT included', plus: '+ VAT' },
} as const;

/** The tax label next to a price. Nahuatl pages use the Spanish legal term. */
export function ivaLabel(price: DisplayPrice, lang: 'es' | 'en' | 'nah' = 'es'): string {
    const labels = lang === 'en' ? IVA_LABELS.en : IVA_LABELS.es;
    return price.ivaIncluded ? labels.included : labels.plus;
}

/** Unit plus tax label, e.g. "MXN/mes, IVA incluido" or "MXN/mes + IVA". */
export function priceUnitLabel(unit: string, price: DisplayPrice, lang: 'es' | 'en' | 'nah' = 'es'): string {
    const label = ivaLabel(price, lang);
    return price.ivaIncluded ? `${unit}, ${label}` : `${unit} ${label}`;
}

export async function fetchTezcaPrices(fetchImpl: typeof fetch = fetch): Promise<TezcaPrices> {
    const base = DHANAM_API_URL.replace(/\/+$/, '').replace(/\/v1$/, '');
    const res = await fetchImpl(`${base}/v1/billing/catalog/tezca`);
    if (!res.ok) throw new Error(`Dhanam catalog answered ${res.status}`);
    const body = (await res.json()) as {
        tiers?: Array<{ slug: string; prices?: unknown; grossPrices?: unknown }>;
    };
    const prices: TezcaPrices = {};
    for (const tier of Array.isArray(body.tiers) ? body.tiers : []) {
        prices[tier.slug] = catalogDisplayPrice(tier, 'monthly');
    }
    return prices;
}

/** Format MXN centavos as whole pesos, e.g. 19900 -> "$199". */
export function formatMxnCentavos(centavos: number): string {
    return `$${Math.round(centavos / 100).toLocaleString('en-US')}`;
}

/** Catalog prices for the page: null while loading, `failed` if unreachable. */
export function useTezcaPrices(): { prices: TezcaPrices | null; failed: boolean } {
    const [prices, setPrices] = useState<TezcaPrices | null>(null);
    const [failed, setFailed] = useState(false);
    useEffect(() => {
        let cancelled = false;
        fetchTezcaPrices()
            .then((p) => {
                if (!cancelled) setPrices(p);
            })
            .catch(() => {
                if (!cancelled) setFailed(true);
            });
        return () => {
            cancelled = true;
        };
    }, []);
    return { prices, failed };
}
