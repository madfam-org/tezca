'use client';

import { getCheckoutUrl, type TezaTier } from '@/lib/billing';

interface UpgradeBannerProps {
  /** Feature name that triggered the gate (e.g. "API keys", "Bulk download") */
  feature: string;
  /** User's current tier (from session) */
  currentTier: TezaTier;
  /** User ID for checkout URL */
  userId?: string;
}

/**
 * Inline banner shown when a user hits a pro-gated feature.
 *
 * Only renders for non-pro users. Uses Dhanam checkout for upgrade.
 */
export function UpgradeBanner({ feature, currentTier, userId }: UpgradeBannerProps) {
  if (currentTier === 'pro' || currentTier === 'madfam') {
    return null;
  }

  const returnUrl = typeof window !== 'undefined' ? window.location.href : undefined;
  const checkoutUrl = getCheckoutUrl('pro', userId, returnUrl);

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
            {feature} requires Tezca Pro
          </p>
          <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
            Upgrade to access {feature.toLowerCase()}, unlimited search results, and more.
          </p>
        </div>
        <a
          href={checkoutUrl}
          className="shrink-0 rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 transition-colors"
        >
          Upgrade to Pro
        </a>
      </div>
    </div>
  );
}
