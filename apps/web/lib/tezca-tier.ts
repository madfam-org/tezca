export type UserTier = 'anon' | 'free_member' | 'community' | 'essentials' | 'academic' | 'institutional' | 'madfam';

/** A signed-in Janua user with no Tezca entitlement. */
export const JANUA_FREE_TIER: UserTier = 'free_member';

const TEZCA_ENTITLEMENT_PREFIX = 'tezca:';

/**
 * Values a Tezca entitlement claim may carry, mapped to the tier Tezca gates on.
 * Mirrors `JANUA_CLAIM_TIERS` in apps/api/middleware/tier_permissions.py.
 * Anything else reads as the free tier: the claim fails closed.
 */
const CLAIM_TIERS: Record<string, UserTier> = {
    free: 'free_member',
    free_member: 'free_member',
    community: 'community',
    essentials: 'essentials',
    academic: 'academic',
    institutional: 'institutional',
    // Unsellable or legacy catalog tiers keep the level they already had.
    pro: 'academic',
    pro_plus: 'academic',
    premium: 'academic',
    enterprise: 'academic',
    // MADFAM operators and service accounts.
    madfam: 'madfam',
    internal: 'madfam',
};

function mapClaimTier(value: unknown): UserTier {
    if (typeof value !== 'string') return JANUA_FREE_TIER;
    const key = value.trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(CLAIM_TIERS, key) ? CLAIM_TIERS[key] : JANUA_FREE_TIER;
}

/**
 * Resolve a Janua user's Tezca tier from Tezca's OWN entitlement claims:
 * `tezca_tier`, else a `tezca:<tier>` entry in `madfam_entitled_products`,
 * else the free tier. The generic `tier`/`plan` claims are never read: they
 * summarize whatever product the org pays for, so reading them would hand
 * Tezca access to buyers of other products.
 */
export function resolveTezcaTier(claims: Record<string, unknown> | null | undefined): UserTier {
    if (!claims || typeof claims !== 'object') return JANUA_FREE_TIER;

    const own = claims.tezca_tier;
    if (own !== undefined && own !== null) return mapClaimTier(own);

    const entitled = claims.madfam_entitled_products;
    if (Array.isArray(entitled)) {
        const entry = entitled.find(
            (e): e is string => typeof e === 'string' && e.startsWith(TEZCA_ENTITLEMENT_PREFIX),
        );
        if (entry) return mapClaimTier(entry.slice(TEZCA_ENTITLEMENT_PREFIX.length));
    }

    return JANUA_FREE_TIER;
}
