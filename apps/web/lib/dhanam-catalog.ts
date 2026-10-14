'use client';

// Tezca's prices come from Dhanam's public catalog: the amounts Dhanam's
// checkout charges (owner rulings G1-1 and 2026-10-14). Pages render these
// instead of typed figures, and a failed read never falls back to a number.
import { useEffect, useState } from 'react';

const DHANAM_API_URL = process.env.NEXT_PUBLIC_DHANAM_API_URL || 'https://api.dhan.am';

/** Monthly MXN price in centavos per catalog tier slug; null when unpriced. */
export type TezcaPrices = Record<string, number | null>;

export async function fetchTezcaPrices(fetchImpl: typeof fetch = fetch): Promise<TezcaPrices> {
    const base = DHANAM_API_URL.replace(/\/+$/, '').replace(/\/v1$/, '');
    const res = await fetchImpl(`${base}/v1/billing/catalog/tezca`);
    if (!res.ok) throw new Error(`Dhanam catalog answered ${res.status}`);
    const body = (await res.json()) as {
        tiers?: Array<{ slug: string; prices?: { MXN?: { monthly?: number | null } } }>;
    };
    const prices: TezcaPrices = {};
    for (const tier of Array.isArray(body.tiers) ? body.tiers : []) {
        const monthly = tier.prices?.MXN?.monthly;
        prices[tier.slug] = typeof monthly === 'number' && monthly > 0 ? monthly : null;
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
