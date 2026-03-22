'use client';

import { useEffect } from 'react';
import { Check, ArrowRight, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, Badge, Button } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { TierComparison } from '@/components/TierComparison';
import { PRICING, PROMO } from '@/lib/pricing';
import { getTrialCheckoutUrl } from '@/lib/billing';
import { MONETIZATION_ENABLED } from '@/lib/config';
import { InterestGate } from '@/components/InterestGate';
import { JsonLd } from '@/components/JsonLd';
import { trackEvent } from '@/lib/analytics/posthog';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

const content = {
    es: {
        title: 'Planes y precios',
        subtitle: 'Accede a la legislacion mexicana con el plan ideal para ti.',
        promoBanner: `${PROMO.trialDaysNoCc}+${PROMO.trialDaysWithCc}: ${PROMO.trialDaysNoCc} dias gratis \u00b7 ${PROMO.trialDaysWithCc} dias con tarjeta \u00b7 ${PROMO.promoMonths} meses al mejor precio`,
        freeMember: 'Free Member',
        freeMemberPrice: 'Gratis',
        freeMemberDesc: 'Para explorar la plataforma sin compromiso.',
        freeMemberCta: 'Crear cuenta',
        essentials: 'Essentials',
        essentialsDesc: 'Investigadores individuales con necesidades basicas.',
        academic: 'Academic',
        academicDesc: 'Instituciones academicas e investigadores avanzados.',
        institutional: 'Institutional',
        institutionalDesc: 'Gobierno, empresas y organizaciones grandes.',
        popular: 'Popular',
        trialCta: `Prueba gratis ${PROMO.trialDaysNoCc} dias`,
        perMonth: '/mes',
        promoFootnote: (price: number) =>
            `Primeros ${PROMO.promoMonths} meses. Despues MXN$${price}/mes`,
        compareTitle: 'Comparacion detallada',
        faqTitle: 'Preguntas frecuentes',
        faq: [
            {
                q: '\u00bfPuedo probar gratis antes de pagar?',
                a: `Si. Todos los planes de pago incluyen ${PROMO.trialDaysNoCc} dias gratis sin tarjeta de credito y ${PROMO.trialDaysWithCc} dias adicionales con tarjeta.`,
            },
            {
                q: '\u00bfPuedo cambiar de plan en cualquier momento?',
                a: 'Si. Puedes actualizar o cancelar tu plan en cualquier momento desde tu cuenta.',
            },
            {
                q: '\u00bfQue metodos de pago aceptan?',
                a: 'Aceptamos tarjetas de credito y debito (Visa, Mastercard, American Express) a traves de nuestra pasarela de pagos segura.',
            },
            {
                q: '\u00bfLos precios incluyen IVA?',
                a: 'Los precios mostrados no incluyen IVA. El impuesto se calcula al momento del pago segun tu ubicacion.',
            },
        ],
        features: {
            free_member: ['Busqueda basica (25 resultados)', 'Descarga TXT y PDF', 'Acceso API'],
            essentials: ['50 resultados por pagina', 'Descarga TXT, PDF y JSON', 'Acceso API', 'Claves API'],
            academic: ['100 resultados por pagina', 'Descarga LaTeX', 'Descarga masiva', 'Analisis de busqueda'],
            institutional: ['1,000 resultados por pagina', 'DOCX y EPUB', 'Webhooks', 'API de grafo'],
        },
    },
    en: {
        title: 'Plans and pricing',
        subtitle: 'Access Mexican legislation with the ideal plan for you.',
        promoBanner: `${PROMO.trialDaysNoCc}+${PROMO.trialDaysWithCc}: ${PROMO.trialDaysNoCc} days free \u00b7 ${PROMO.trialDaysWithCc} days with card \u00b7 ${PROMO.promoMonths} months at the best price`,
        freeMember: 'Free Member',
        freeMemberPrice: 'Free',
        freeMemberDesc: 'Explore the platform with no commitment.',
        freeMemberCta: 'Create account',
        essentials: 'Essentials',
        essentialsDesc: 'Individual researchers with basic needs.',
        academic: 'Academic',
        academicDesc: 'Academic institutions and advanced researchers.',
        institutional: 'Institutional',
        institutionalDesc: 'Government, enterprises, and large organizations.',
        popular: 'Popular',
        trialCta: `Try free for ${PROMO.trialDaysNoCc} days`,
        perMonth: '/mo',
        promoFootnote: (price: number) =>
            `First ${PROMO.promoMonths} months. Then MXN$${price}/mo`,
        compareTitle: 'Detailed comparison',
        faqTitle: 'Frequently asked questions',
        faq: [
            {
                q: 'Can I try for free before paying?',
                a: `Yes. All paid plans include ${PROMO.trialDaysNoCc} free days without a credit card and ${PROMO.trialDaysWithCc} additional days with a card.`,
            },
            {
                q: 'Can I change plans at any time?',
                a: 'Yes. You can upgrade or cancel your plan at any time from your account.',
            },
            {
                q: 'What payment methods do you accept?',
                a: 'We accept credit and debit cards (Visa, Mastercard, American Express) through our secure payment gateway.',
            },
            {
                q: 'Do prices include tax?',
                a: 'Prices shown do not include tax. Tax is calculated at checkout based on your location.',
            },
        ],
        features: {
            free_member: ['Basic search (25 results)', 'TXT and PDF download', 'API access'],
            essentials: ['50 results per page', 'TXT, PDF, and JSON download', 'API access', 'API keys'],
            academic: ['100 results per page', 'LaTeX download', 'Bulk download', 'Search analytics'],
            institutional: ['1,000 results per page', 'DOCX and EPUB', 'Webhooks', 'Graph API'],
        },
    },
    nah: {
        title: 'Tlaxtlahuilli ihuan patiyotl',
        subtitle: 'Xicahci in mexihcatl tenahuatilli ica motlaxtlahuil.',
        promoBanner: `${PROMO.trialDaysNoCc}+${PROMO.trialDaysWithCc}: ${PROMO.trialDaysNoCc} tonalli \u00b7 ${PROMO.trialDaysWithCc} tonalli \u00b7 ${PROMO.promoMonths} metztli`,
        freeMember: 'Free Member',
        freeMemberPrice: 'Tlanahuatilli',
        freeMemberDesc: 'Xicyeyeco in tlahcuilolpan.',
        freeMemberCta: 'Xicchihua mocuenta',
        essentials: 'Essentials',
        essentialsDesc: 'Tlamatinimeh ica tlanequiliztli.',
        academic: 'Academic',
        academicDesc: 'Tlamachtilcalli ihuan tlamatinimeh.',
        institutional: 'Institutional',
        institutionalDesc: 'Tlatocayotl ihuan hueyi calli.',
        popular: 'Popular',
        trialCta: `Xicyeyeco ${PROMO.trialDaysNoCc} tonalli`,
        perMonth: '/metztli',
        promoFootnote: (price: number) =>
            `${PROMO.promoMonths} metztli. Zatepan MXN$${price}/metztli`,
        compareTitle: 'Tlananamicoliztli',
        faqTitle: 'Tlatlaniliztli',
        faq: [
            {
                q: 'Huel nicyeyecoz?',
                a: `Quemah. Mochi tlaxtlahuilli quipia ${PROMO.trialDaysNoCc} tonalli ihuan ${PROMO.trialDaysWithCc} tonalli.`,
            },
            {
                q: 'Huel nicpatla notlaxtlahuil?',
                a: 'Quemah. Huel ticpatla noso ticcahua quemanian.',
            },
        ],
        features: {
            free_member: ['Tlatemoliztli (25)', 'TXT ihuan PDF', 'API'],
            essentials: ['50 tlanextiliztli', 'TXT, PDF, JSON', 'API', 'API tlaquimilolli'],
            academic: ['100 tlanextiliztli', 'LaTeX', 'Huei temohuiliztli', 'Tlatemoliztli tlaixmatiliztli'],
            institutional: ['1,000 tlanextiliztli', 'DOCX, EPUB', 'Webhooks', 'API grafo'],
        },
    },
};

const preMonetizationSubtitle = {
    es: 'Próximamente — regístrate para acceso anticipado.',
    en: 'Coming soon — sign up for early access.',
    nah: 'Hualaz niman — xicmotocāyōti.',
};

const TIER_FEATURE_KEY: Record<string, string> = {
    essentials: 'advanced_search',
    academic: 'latex_export',
    institutional: 'webhooks',
};

const comingSoonLabel = {
    es: 'Próximamente',
    en: 'Coming soon',
    nah: 'Hualaz niman',
};

type TierKey = 'free_member' | 'essentials' | 'academic' | 'institutional';

function FaqSection({ faq, title }: { faq: { q: string; a: string }[]; title: string }) {
    return (
        <section className="mt-16 max-w-3xl mx-auto">
            <h2 className="text-2xl font-bold text-center mb-8">{title}</h2>
            <div className="space-y-4">
                {faq.map((item, i) => (
                    <details key={i} className="group rounded-lg border border-border bg-card">
                        <summary className="flex cursor-pointer items-center justify-between p-4 text-sm font-medium">
                            {item.q}
                            <span className="ml-2 transition-transform group-open:rotate-45 text-muted-foreground">+</span>
                        </summary>
                        <div className="px-4 pb-4 text-sm text-muted-foreground">
                            {item.a}
                        </div>
                    </details>
                ))}
            </div>
        </section>
    );
}

export default function PreciosPage() {
    const { lang } = useLang();
    const { userId, isAuthenticated, tier } = useAuth();
    const t = content[lang];

    useEffect(() => {
        trackEvent('pricing.page_viewed', { is_authenticated: isAuthenticated, tier, monetization_enabled: MONETIZATION_ENABLED });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- track once on mount
    }, []);

    const tiers: { key: TierKey; isPopular?: boolean }[] = [
        { key: 'free_member' },
        { key: 'essentials' },
        { key: 'academic', isPopular: true },
        { key: 'institutional' },
    ];

    const getPrice = (tierKey: TierKey) => {
        if (tierKey === 'free_member') return null;
        return PRICING[tierKey];
    };

    const getCtaHref = (tierKey: TierKey) => {
        if (tierKey === 'free_member') {
            return isAuthenticated ? '/cuenta' : '/login';
        }
        return getTrialCheckoutUrl(
            tierKey,
            userId ?? undefined,
            typeof window !== 'undefined' ? window.location.href : undefined,
        );
    };

    const getCtaLabel = (tierKey: TierKey) => {
        if (tierKey === 'free_member') return t.freeMemberCta;
        return t.trialCta;
    };

    const getTierName = (tierKey: TierKey) => {
        return t[tierKey as keyof typeof t] as string;
    };

    const getTierDesc = (tierKey: TierKey) => {
        const descKey = `${tierKey}Desc` as keyof typeof t;
        return t[descKey] as string;
    };

    return (
        <div className="min-h-screen bg-background">
            <JsonLd data={{
                '@context': 'https://schema.org',
                '@type': 'BreadcrumbList',
                itemListElement: [
                    { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${siteUrl}/` },
                    { '@type': 'ListItem', position: 2, name: 'Precios', item: `${siteUrl}/precios` },
                ],
            }} />
            <JsonLd data={{
                '@context': 'https://schema.org',
                '@type': 'FAQPage',
                mainEntity: content.es.faq.map(item => ({
                    '@type': 'Question',
                    name: item.q,
                    acceptedAnswer: { '@type': 'Answer', text: item.a },
                })),
            }} />
            {/* Header */}
            <div className="bg-gradient-to-b from-primary/5 to-background pt-16 pb-8 text-center px-4">
                <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">{t.title}</h1>
                <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
                    {MONETIZATION_ENABLED ? t.subtitle : preMonetizationSubtitle[lang]}
                </p>

                {/* Promo banner — only when monetization is enabled */}
                {MONETIZATION_ENABLED && (
                    <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-2 text-sm font-medium text-primary">
                        <Sparkles className="h-4 w-4" />
                        {t.promoBanner}
                    </div>
                )}
            </div>

            {/* Pricing cards */}
            <div className="container mx-auto px-4 sm:px-6 -mt-2">
                <div className="grid gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-4 max-w-6xl mx-auto">
                    {tiers.map(({ key, isPopular }) => {
                        const price = getPrice(key);
                        return (
                            <Card
                                key={key}
                                className={`relative flex flex-col ${
                                    isPopular
                                        ? 'border-primary ring-2 ring-primary/20 shadow-lg'
                                        : ''
                                }`}
                            >
                                {isPopular && (
                                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                                        <Badge className="bg-primary text-primary-foreground text-xs px-3">
                                            {t.popular}
                                        </Badge>
                                    </div>
                                )}
                                {!MONETIZATION_ENABLED && key !== 'free_member' && (
                                    <div className="absolute -top-3 right-4">
                                        <Badge variant="outline" className="text-xs px-2 bg-background">
                                            {comingSoonLabel[lang]}
                                        </Badge>
                                    </div>
                                )}
                                <CardContent className="flex flex-col flex-1 p-6">
                                    <h3 className="font-bold text-lg">{getTierName(key)}</h3>
                                    <p className="mt-1 text-sm text-muted-foreground">
                                        {getTierDesc(key)}
                                    </p>

                                    {/* Price — only when monetization is enabled */}
                                    {MONETIZATION_ENABLED && (
                                        <div className="mt-4 mb-4">
                                            {price ? (
                                                <>
                                                    <div className="flex items-baseline gap-1">
                                                        <span className="text-3xl font-bold">
                                                            ${price.promo}
                                                        </span>
                                                        <span className="text-sm text-muted-foreground">
                                                            {price.currency}
                                                            {t.perMonth}
                                                        </span>
                                                        <span className="text-xs text-muted-foreground">*</span>
                                                    </div>
                                                    <p className="mt-1 text-xs text-muted-foreground">
                                                        {t.promoFootnote(price.monthly)}
                                                    </p>
                                                </>
                                            ) : (
                                                <div className="flex items-baseline gap-1">
                                                    <span className="text-3xl font-bold">
                                                        {t.freeMemberPrice}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    {!MONETIZATION_ENABLED && key === 'free_member' && (
                                        <div className="mt-4 mb-4">
                                            <div className="flex items-baseline gap-1">
                                                <span className="text-3xl font-bold">
                                                    {t.freeMemberPrice}
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Feature list */}
                                    <ul className="space-y-2 mb-6 flex-1">
                                        {t.features[key].map((feature, i) => (
                                            <li key={i} className="flex items-start gap-2 text-sm">
                                                <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                                                <span className="text-muted-foreground">{feature}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    {/* CTA */}
                                    {MONETIZATION_ENABLED || key === 'free_member' ? (
                                        <Link href={getCtaHref(key)} onClick={() => trackEvent('pricing.cta_clicked', { tier_key: key, is_authenticated: isAuthenticated })}>
                                            <Button
                                                className="w-full gap-2 group"
                                                variant={isPopular ? 'default' : 'outline'}
                                            >
                                                {getCtaLabel(key)}
                                                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                                            </Button>
                                        </Link>
                                    ) : (
                                        <InterestGate
                                            variant="inline"
                                            featureKey={TIER_FEATURE_KEY[key] ?? 'advanced_search'}
                                            sourcePage="pricing"
                                            showUseCase={false}
                                        />
                                    )}
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            </div>

            {/* Detailed comparison */}
            <div className="container mx-auto px-4 sm:px-6 mt-16">
                <h2 className="text-2xl font-bold text-center mb-8">{t.compareTitle}</h2>
                <TierComparison showPricing={MONETIZATION_ENABLED} />
            </div>

            {/* FAQ */}
            <div className="container mx-auto px-4 sm:px-6 pb-16">
                <FaqSection faq={t.faq} title={t.faqTitle} />
            </div>
        </div>
    );
}
