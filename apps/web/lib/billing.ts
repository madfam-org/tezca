/**
 * Dhanam billing integration for Tezca.
 *
 * Provides checkout URL generation for tier upgrades.
 * Uses direct URL construction (no SDK dependency needed for this minimal use case).
 */

const DHANAM_CHECKOUT_URL =
  process.env.NEXT_PUBLIC_DHANAM_CHECKOUT_URL || 'https://dhanam.madfam.io/checkout';

export type TezaTier = 'essentials' | 'pro' | 'madfam' | null;

/**
 * Build a checkout URL for upgrading to a Tezca tier via Dhanam.
 */
export function getCheckoutUrl(
  plan: 'pro' | 'madfam' = 'pro',
  userId?: string,
  returnUrl?: string,
): string {
  const params = new URLSearchParams({
    plan: `tezca_${plan}`,
    product: 'tezca',
  });
  if (userId) params.set('user_id', userId);
  if (returnUrl) params.set('return_url', returnUrl);
  return `${DHANAM_CHECKOUT_URL}?${params.toString()}`;
}

/**
 * Check if a tier has access to a premium feature.
 */
export function isPremiumTier(tier: TezaTier): boolean {
  return tier === 'pro' || tier === 'madfam';
}
