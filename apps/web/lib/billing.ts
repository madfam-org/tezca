/**
 * Dhanam billing integration for Tezca.
 *
 * Provides checkout URL generation for tier upgrades.
 * Uses direct URL construction (no SDK dependency needed for this minimal use case).
 */

const DHANAM_CHECKOUT_URL =
  process.env.NEXT_PUBLIC_DHANAM_CHECKOUT_URL || 'https://dhanam.madfam.io/checkout';

export type TezaTier = 'free_member' | 'community' | 'essentials' | 'academic' | 'institutional' | 'madfam' | null;

/**
 * Build a checkout URL for upgrading to a Tezca tier via Dhanam.
 */
export function getCheckoutUrl(
  plan: 'essentials' | 'academic' | 'institutional' | 'madfam' = 'academic',
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
 * Check if a tier has paid access (essentials+).
 */
export function hasPaidAccess(tier: TezaTier): boolean {
  return tier === 'essentials' || tier === 'academic' || tier === 'institutional' || tier === 'madfam';
}

/**
 * Build a trial checkout URL (no credit card required for initial days).
 */
export function getTrialCheckoutUrl(
  plan: 'essentials' | 'academic' | 'institutional',
  userId?: string,
  returnUrl?: string,
): string {
  const params = new URLSearchParams({
    plan: `tezca_${plan}`,
    product: 'tezca',
    mode: 'trial_cc',
  });
  if (userId) params.set('user_id', userId);
  if (returnUrl) params.set('return_url', returnUrl);
  return `${DHANAM_CHECKOUT_URL}?${params.toString()}`;
}

/**
 * Build a promo checkout URL (discounted first months).
 */
export function getPromoCheckoutUrl(
  plan: 'essentials' | 'academic' | 'institutional',
  userId?: string,
  returnUrl?: string,
): string {
  const params = new URLSearchParams({
    plan: `tezca_${plan}_promo`,
    product: 'tezca',
  });
  if (userId) params.set('user_id', userId);
  if (returnUrl) params.set('return_url', returnUrl);
  return `${DHANAM_CHECKOUT_URL}?${params.toString()}`;
}
