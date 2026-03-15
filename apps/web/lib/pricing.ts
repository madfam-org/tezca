export const PRICING = {
  essentials:    { monthly: 99,  promo: 31, currency: 'MXN' },
  academic:      { monthly: 199, promo: 32, currency: 'MXN' },
  institutional: { monthly: 499, promo: 33, currency: 'MXN' },
} as const;

export const PROMO = {
  trialDaysNoCc: 3,
  trialDaysWithCc: 21,
  promoMonths: 3,
} as const;

export type PricingTier = keyof typeof PRICING;
