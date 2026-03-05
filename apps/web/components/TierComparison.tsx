'use client';

import { Check, X, ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { Button, Badge, Card, CardContent } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { getCheckoutUrl } from '@/lib/billing';

const content = {
    es: {
        title: 'Compara los planes de Tezca',
        subtitle: 'Elige el plan que mejor se adapte a tus necesidades',
        essentials: 'Essentials',
        community: 'Community',
        pro: 'Pro',
        free: 'Gratis',
        current: 'Tu plan',
        popular: 'Popular',
        ctaFree: 'Empieza gratis',
        ctaUpgrade: 'Mejora tu plan',
        features: {
            search_results: 'Resultados por página',
            export_txt: 'Descargar TXT',
            export_pdf: 'Descargar PDF',
            export_premium: 'LaTeX, DOCX, EPUB, JSON',
            api_access: 'Acceso API',
            bulk_download: 'Descarga masiva',
            webhooks: 'Webhooks',
            analytics: 'Análisis de búsqueda',
        },
    },
    en: {
        title: 'Compare Tezca plans',
        subtitle: 'Choose the plan that best fits your needs',
        essentials: 'Essentials',
        community: 'Community',
        pro: 'Pro',
        free: 'Free',
        current: 'Your plan',
        popular: 'Popular',
        ctaFree: 'Start free',
        ctaUpgrade: 'Upgrade',
        features: {
            search_results: 'Results per page',
            export_txt: 'Download TXT',
            export_pdf: 'Download PDF',
            export_premium: 'LaTeX, DOCX, EPUB, JSON',
            api_access: 'API access',
            bulk_download: 'Bulk download',
            webhooks: 'Webhooks',
            analytics: 'Search analytics',
        },
    },
    nah: {
        title: 'Xicnānamiqui Tezca tlaxtlahuīlli',
        subtitle: 'Xicpēpena in tlaxtlahuīlli',
        essentials: 'Essentials',
        community: 'Community',
        pro: 'Pro',
        free: 'Tlanāhuatīlli',
        current: 'Mocuenta',
        popular: 'Popular',
        ctaFree: 'Xipēhua',
        ctaUpgrade: 'Xicmelahua',
        features: {
            search_results: 'Tlanextīliztli',
            export_txt: 'Xictēmōhui TXT',
            export_pdf: 'Xictēmōhui PDF',
            export_premium: 'LaTeX, DOCX, EPUB, JSON',
            api_access: 'API',
            bulk_download: 'Huēyi tēmōhuiliztli',
            webhooks: 'Webhooks',
            analytics: 'Tlanextīliztli tlaixmatiliztli',
        },
    },
};

type FeatureKey = keyof typeof content.en.features;

interface FeatureRow {
    key: FeatureKey;
    essentials: string | boolean;
    community: string | boolean;
    pro: string | boolean;
}

const FEATURES: FeatureRow[] = [
    { key: 'search_results', essentials: '25', community: '100', pro: '100' },
    { key: 'export_txt', essentials: true, community: true, pro: true },
    { key: 'export_pdf', essentials: true, community: true, pro: true },
    { key: 'export_premium', essentials: false, community: false, pro: true },
    { key: 'api_access', essentials: true, community: true, pro: true },
    { key: 'bulk_download', essentials: false, community: true, pro: true },
    { key: 'webhooks', essentials: false, community: true, pro: true },
    { key: 'analytics', essentials: false, community: false, pro: true },
];

interface TierComparisonProps {
    className?: string;
    compact?: boolean;
}

export function TierComparison({ className = '', compact = false }: TierComparisonProps) {
    const { lang } = useLang();
    const { tier, userId, isAuthenticated } = useAuth();
    const t = content[lang];

    const tiers = ['essentials', 'community', 'pro'] as const;

    const getCheckoutHref = (targetTier: 'essentials' | 'community' | 'pro') => {
        if (!isAuthenticated) return '/login';
        if (targetTier === 'essentials') return '/cuenta';
        return getCheckoutUrl(targetTier, userId ?? undefined, typeof window !== 'undefined' ? window.location.href : undefined);
    };

    const isCurrent = (planTier: string) => tier === planTier;
    const isDowngrade = (planTier: string) => {
        const rank: Record<string, number> = { anon: 0, essentials: 1, community: 2, pro: 3, madfam: 4 };
        return (rank[planTier] ?? 0) <= (rank[tier] ?? 0);
    };

    const renderValue = (val: string | boolean) => {
        if (typeof val === 'string') return <span className="text-sm font-medium">{val}</span>;
        if (val) return <Check className="h-4 w-4 text-primary mx-auto" />;
        return <X className="h-4 w-4 text-muted-foreground/30 mx-auto" />;
    };

    if (compact) {
        return (
            <div className={`grid grid-cols-3 gap-2 text-center text-xs ${className}`}>
                {tiers.map((planTier) => (
                    <div
                        key={planTier}
                        className={`rounded-lg p-2 ${isCurrent(planTier) ? 'bg-primary/10 ring-1 ring-primary/30' : 'bg-muted/50'}`}
                    >
                        <div className="font-bold mb-0.5">{t[planTier]}</div>
                        {isCurrent(planTier) && (
                            <Badge variant="outline" className="text-[10px] px-1 py-0 mb-0.5">{t.current}</Badge>
                        )}
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div className={className}>
            {/* Desktop table */}
            <div className="hidden sm:block">
                <table className="w-full text-sm">
                    <thead>
                        <tr>
                            <th className="text-left pb-4 pr-4 w-1/3" />
                            {tiers.map((planTier) => (
                                <th key={planTier} className="pb-4 text-center w-[22%]">
                                    <div className="space-y-1">
                                        <div className="font-bold text-base">
                                            {t[planTier]}
                                        </div>
                                        {planTier === 'essentials' && (
                                            <Badge variant="secondary" className="text-xs">{t.free}</Badge>
                                        )}
                                        {planTier === 'community' && (
                                            <Badge className="text-xs bg-primary text-primary-foreground">{t.popular}</Badge>
                                        )}
                                        {isCurrent(planTier) && (
                                            <Badge variant="outline" className="text-xs">{t.current}</Badge>
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {FEATURES.map((feature) => (
                            <tr key={feature.key} className="border-t border-border/50">
                                <td className="py-3 pr-4 text-muted-foreground">
                                    {t.features[feature.key]}
                                </td>
                                {tiers.map((planTier) => (
                                    <td key={planTier} className="py-3 text-center">
                                        {renderValue(feature[planTier])}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                    <tfoot>
                        <tr className="border-t">
                            <td className="pt-4" />
                            {tiers.map((planTier) => (
                                <td key={planTier} className="pt-4 text-center">
                                    {!isDowngrade(planTier) && (
                                        <Link href={getCheckoutHref(planTier)}>
                                            <Button
                                                size="sm"
                                                variant={planTier === 'community' ? 'default' : 'outline'}
                                                className="gap-1"
                                            >
                                                <Sparkles className="h-3 w-3" />
                                                {!isAuthenticated ? t.ctaFree : t.ctaUpgrade}
                                            </Button>
                                        </Link>
                                    )}
                                </td>
                            ))}
                        </tr>
                    </tfoot>
                </table>
            </div>

            {/* Mobile stacked cards */}
            <div className="sm:hidden space-y-3">
                {tiers.map((planTier) => {
                    const isHighlighted = planTier === 'community';
                    return (
                        <Card
                            key={planTier}
                            className={`${isHighlighted ? 'border-primary ring-1 ring-primary/20' : ''} ${isCurrent(planTier) ? 'bg-primary/5' : ''}`}
                        >
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold">{t[planTier]}</span>
                                        {planTier === 'essentials' && (
                                            <Badge variant="secondary" className="text-xs">{t.free}</Badge>
                                        )}
                                        {isHighlighted && (
                                            <Badge className="text-xs bg-primary text-primary-foreground">{t.popular}</Badge>
                                        )}
                                    </div>
                                    {isCurrent(planTier) && (
                                        <Badge variant="outline" className="text-xs">{t.current}</Badge>
                                    )}
                                </div>
                                <ul className="space-y-1.5 text-sm mb-3">
                                    {FEATURES.map((feature) => {
                                        const val = feature[planTier];
                                        if (val === false) return null;
                                        return (
                                            <li key={feature.key} className="flex items-center gap-2">
                                                <Check className="h-3.5 w-3.5 text-primary shrink-0" />
                                                <span className="text-muted-foreground">
                                                    {t.features[feature.key]}
                                                    {typeof val === 'string' && `: ${val}`}
                                                </span>
                                            </li>
                                        );
                                    })}
                                </ul>
                                {!isDowngrade(planTier) && (
                                    <Link href={getCheckoutHref(planTier)} className="block">
                                        <Button
                                            size="sm"
                                            variant={isHighlighted ? 'default' : 'outline'}
                                            className="w-full gap-1"
                                        >
                                            <Sparkles className="h-3 w-3" />
                                            {!isAuthenticated ? t.ctaFree : t.ctaUpgrade}
                                            <ArrowRight className="h-3 w-3" />
                                        </Button>
                                    </Link>
                                )}
                            </CardContent>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
}
