// Pricing anchored on Tulana competitive intel (v0.1, 2026-04-25):
// - Mexican legal-tech competitor median ~1,478 MXN/mo (vLex Mexico Pro
//   $85 USD ≈ 1,445 MXN, Doctrina AI Pro $30 USD ≈ 510 MXN, LegalTracker
//   MX $3,500 MXN flat-API).
// - Tulana methodology: 0.8x competitor median = ~1,180 MXN ceiling for
//   the standard-tier; we price Essentials below that and Institutional
//   above (premium for the 100k calls/mo bucket carries enterprise WTP).
// - Tier-name aliases preserved: essentials maps to tezca_essentials in
//   apps/api/billing_views PLAN_TO_TIER. academic maps to tezca_academic.
//   institutional maps to tezca_institutional.
// - Confidence: "low" until Tulana v0.2 ships WTP automation. Operator
//   should re-validate via PhyndCRM Van Westendorp campaign before
//   any major price change.
export const PRICING = {
  essentials:    { monthly: 199,  promo: 31, currency: 'MXN' },
  academic:      { monthly: 599,  promo: 32, currency: 'MXN' },
  institutional: { monthly: 1999, promo: 33, currency: 'MXN' },
} as const;

export const PROMO = {
  trialDaysNoCc: 3,
  trialDaysWithCc: 21,
  promoMonths: 3,
} as const;

export type PricingTier = keyof typeof PRICING;
