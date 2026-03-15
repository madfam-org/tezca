'use client';

import { Check, X, ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { Button, Badge, Card, CardContent } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { getCheckoutUrl } from '@/lib/billing';
import { PRICING } from '@/lib/pricing';

const content = {
    es: {
        title: 'Compara los planes de Tezca',
        subtitle: 'Elige el plan que mejor se adapte a tus necesidades',
        free_member: 'Free Member',
        essentials: 'Essentials',
        academic: 'Academic',
        institutional: 'Institutional',
        free: 'Gratis',
        current: 'Tu plan',
        popular: 'Popular',
        ctaFree: 'Empieza gratis',
        ctaUpgrade: 'Mejora tu plan',
        perMonth: '/mes',
        promoNote: 'Primeros 3 meses',
        features: {
            search_results: 'Resultados por pagina',
            export_txt: 'Descargar TXT',
            export_pdf: 'Descargar PDF/JSON',
            export_latex: 'Descargar LaTeX',
            export_premium: 'DOCX, EPUB',
            api_access: 'Acceso API',
            bulk_download: 'Descarga masiva',
            webhooks: 'Webhooks',
            analytics: 'Analisis de busqueda',
            graph_api: 'API de grafo',
        },
    },
    en: {
        title: 'Compare Tezca plans',
        subtitle: 'Choose the plan that best fits your needs',
        free_member: 'Free Member',
        essentials: 'Essentials',
        academic: 'Academic',
        institutional: 'Institutional',
        free: 'Free',
        current: 'Your plan',
        popular: 'Popular',
        ctaFree: 'Start free',
        ctaUpgrade: 'Upgrade',
        perMonth: '/mo',
        promoNote: 'First 3 months',
        features: {
            search_results: 'Results per page',
            export_txt: 'Download TXT',
            export_pdf: 'Download PDF/JSON',
            export_latex: 'Download LaTeX',
            export_premium: 'DOCX, EPUB',
            api_access: 'API access',
            bulk_download: 'Bulk download',
            webhooks: 'Webhooks',
            analytics: 'Search analytics',
            graph_api: 'Graph API',
        },
    },
    nah: {
        title: 'Xicnanamiqui Tezca tlaxtlahuilli',
        subtitle: 'Xicpepena in tlaxtlahuilli',
        free_member: 'Free Member',
        essentials: 'Essentials',
        academic: 'Academic',
        institutional: 'Institutional',
        free: 'Tlanahuatilli',
        current: 'Mocuenta',
        popular: 'Popular',
        ctaFree: 'Xipehua',
        ctaUpgrade: 'Xicmelahua',
        perMonth: '/metztli',
        promoNote: '3 metztli',
        features: {
            search_results: 'Tlanextiliztli',
            export_txt: 'Xictemohui TXT',
            export_pdf: 'Xictemohui PDF/JSON',
            export_latex: 'Xictemohui LaTeX',
            export_premium: 'DOCX, EPUB',
            api_access: 'API',
            bulk_download: 'Hueyi temohuiliztli',
            webhooks: 'Webhooks',
            analytics: 'Tlanextiliztli tlaixmatiliztli',
            graph_api: 'API tlanextiliztli',
        },
    },
};

type FeatureKey = keyof typeof content.en.features;

interface FeatureRow {
    key: FeatureKey;
    free_member: string | boolean;
    essentials: string | boolean;
    academic: string | boolean;
    institutional: string | boolean;
}

const FEATURES: FeatureRow[] = [
    { key: 'search_results', free_member: '25', essentials: '50', academic: '100', institutional: '1,000' },
    { key: 'export_txt', free_member: true, essentials: true, academic: true, institutional: true },
    { key: 'export_pdf', free_member: true, essentials: true, academic: true, institutional: true },
    { key: 'export_latex', free_member: false, essentials: false, academic: true, institutional: true },
    { key: 'export_premium', free_member: false, essentials: false, academic: false, institutional: true },
    { key: 'api_access', free_member: true, essentials: true, academic: true, institutional: true },
    { key: 'bulk_download', free_member: false, essentials: false, academic: true, institutional: true },
    { key: 'webhooks', free_member: false, essentials: false, academic: false, institutional: true },
    { key: 'analytics', free_member: false, essentials: false, academic: true, institutional: true },
    { key: 'graph_api', free_member: false, essentials: false, academic: false, institutional: true },
];

interface TierComparisonProps {
    className?: string;
    compact?: boolean;
    showPricing?: boolean;
}

export function TierComparison({ className = '', compact = false, showPricing = false }: TierComparisonProps) {
    const { lang } = useLang();
    const { tier, userId, isAuthenticated } = useAuth();
    const t = content[lang];

    const tiers = ['free_member', 'essentials', 'academic', 'institutional'] as const;

    const getCheckoutHref = (targetTier: typeof tiers[number]) => {
        if (!isAuthenticated) return '/login';
        if (targetTier === 'free_member') return '/cuenta';
        return getCheckoutUrl(targetTier, userId ?? undefined, typeof window !== 'undefined' ? window.location.href : undefined);
    };

    // Map free_member to community for current-plan detection (community is the auth tier for free users)
    const isCurrent = (planTier: string) => {
        if (planTier === 'free_member') return tier === 'community' || tier === 'anon';
        return tier === planTier;
    };
    const isDowngrade = (planTier: string) => {
        const rank: Record<string, number> = { anon: 0, free_member: 1, community: 1, essentials: 2, academic: 3, institutional: 4, madfam: 5 };
        return (rank[planTier] ?? 0) <= (rank[tier] ?? 0);
    };

    const renderValue = (val: string | boolean) => {
        if (typeof val === 'string') return <span className="text-sm font-medium">{val}</span>;
        if (val) return <Check className="h-4 w-4 text-primary mx-auto" />;
        return <X className="h-4 w-4 text-muted-foreground/30 mx-auto" />;
    };

    const getPriceLabel = (planTier: typeof tiers[number]): string | null => {
        if (planTier === 'free_member') return t.free;
        const priceData = PRICING[planTier];
        return `$${priceData.promo}${t.perMonth}*`;
    };

    if (compact) {
        return (
            <div className={`grid grid-cols-4 gap-2 text-center text-xs ${className}`}>
                {tiers.map((planTier) => (
                    <div
                        key={planTier}
                        className={`rounded-lg p-2 ${isCurrent(planTier) ? 'bg-primary/10 ring-1 ring-primary/30' : 'bg-muted/50'}`}
                    >
                        <div className="font-bold mb-0.5">{t[planTier]}</div>
                        {isCurrent(planTier) && (
                            <Badge variant="outline" className="text-xs px-1.5 py-0 mb-0.5">{t.current}</Badge>
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
                            <th className="text-left pb-4 pr-4 w-1/5" />
                            {tiers.map((planTier) => (
                                <th key={planTier} className="pb-4 text-center w-[20%]">
                                    <div className="space-y-1">
                                        <div className="font-bold text-base">
                                            {t[planTier]}
                                        </div>
                                        {planTier === 'free_member' && (
                                            <Badge variant="secondary" className="text-xs">{t.free}</Badge>
                                        )}
                                        {planTier === 'academic' && (
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
                        {showPricing && (
                            <tr className="border-t border-border/50">
                                <td className="py-3 pr-4 text-muted-foreground font-medium">
                                    {lang === 'en' ? 'Price' : lang === 'nah' ? 'Patiyotl' : 'Precio'}
                                </td>
                                {tiers.map((planTier) => (
                                    <td key={planTier} className="py-3 text-center">
                                        <span className="text-sm font-bold">{getPriceLabel(planTier)}</span>
                                    </td>
                                ))}
                            </tr>
                        )}
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
                    {showPricing && (
                        <tfoot>
                            <tr>
                                <td className="pt-2 text-xs text-muted-foreground" colSpan={5}>
                                    * {t.promoNote}
                                </td>
                            </tr>
                        </tfoot>
                    )}
                    <tfoot>
                        <tr className="border-t">
                            <td className="pt-4" />
                            {tiers.map((planTier) => (
                                <td key={planTier} className="pt-4 text-center">
                                    {!isDowngrade(planTier) && (
                                        <Link href={getCheckoutHref(planTier)}>
                                            <Button
                                                size="sm"
                                                variant={planTier === 'academic' ? 'default' : 'outline'}
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
                    const isHighlighted = planTier === 'academic';
                    return (
                        <Card
                            key={planTier}
                            className={`${isHighlighted ? 'border-primary ring-1 ring-primary/20' : ''} ${isCurrent(planTier) ? 'bg-primary/5' : ''}`}
                        >
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold">{t[planTier]}</span>
                                        {planTier === 'free_member' && (
                                            <Badge variant="secondary" className="text-xs">{t.free}</Badge>
                                        )}
                                        {isHighlighted && (
                                            <Badge className="text-xs bg-primary text-primary-foreground">{t.popular}</Badge>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {showPricing && (
                                            <span className="text-sm font-bold">{getPriceLabel(planTier)}</span>
                                        )}
                                        {isCurrent(planTier) && (
                                            <Badge variant="outline" className="text-xs">{t.current}</Badge>
                                        )}
                                    </div>
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
                {showPricing && (
                    <p className="text-xs text-muted-foreground text-center">* {t.promoNote}</p>
                )}
            </div>
        </div>
    );
}
