'use client';

import { useEffect } from 'react';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';
import { MONETIZATION_ENABLED } from '@/lib/config';
import { InterestGate } from '@/components/InterestGate';
import { TierGate } from '@/components/TierGate';
import { trackEvent } from '@/lib/analytics/posthog';

const INSTITUTIONAL_TIERS = new Set(['institutional', 'madfam']);

export function GraphTierMessage() {
    const { effectiveTier } = useAuth();
    const { lang } = useLang();

    const hasAccess = INSTITUTIONAL_TIERS.has(effectiveTier);

    useEffect(() => {
        if (!hasAccess) {
            trackEvent('graph_tier_message.shown', { tier: effectiveTier, feature_key: 'graph_api' });
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- track once on mount
    }, []);

    if (hasAccess) return null;

    if (!MONETIZATION_ENABLED) {
        return (
            <div className="container mx-auto px-4 sm:px-6 pt-6">
                <InterestGate
                    variant="inline"
                    featureKey="graph_api"
                    sourcePage="graph"
                />
            </div>
        );
    }

    const feature: Record<string, string> = {
        es: 'El grafo interactivo de leyes requiere el plan Institutional.',
        en: 'The interactive law graph requires the Institutional plan.',
        nah: 'In tlanōnotzaliztli grafo monequi Institutional tlaxtlahuīlli.',
    };

    return (
        <div className="container mx-auto px-4 sm:px-6 pt-6">
            <TierGate
                variant="inline"
                requiredTier="institutional"
                feature={feature[lang]}
            />
        </div>
    );
}
