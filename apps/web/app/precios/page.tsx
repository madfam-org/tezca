'use client';

import { useEffect } from 'react';
import { Check, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, Badge, Button } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { TierComparison } from '@/components/TierComparison';
import { formatMxnCentavos, priceUnitLabel, useTezcaPrices, type DisplayPrice } from '@/lib/dhanam-catalog';
import { getCheckoutUrl } from '@/lib/billing';
import { MONETIZATION_ENABLED } from '@/lib/config';
import { InterestGate } from '@/components/InterestGate';
import { JsonLd } from '@/components/JsonLd';
import { trackEvent } from '@/lib/analytics/posthog';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://tezca.mx';

const content = {
    es: {
        title: 'Planes y precios',
        subtitle: 'Accede a la legislacion mexicana con el plan ideal para ti.',
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
        subscribeCta: 'Suscribirme',
        priceAtCheckout: 'Precio al pagar',
        loadingPrice: 'Cargando precio…',
        perMonth: '/mes',
        compareTitle: 'Comparacion detallada',
        faqTitle: 'Preguntas frecuentes',
        faq: [
            {
                q: '\u00bfPuedo probar gratis antes de pagar?',
                a: 'Por ahora no hay prueba gratuita. El plan Free Member es gratis y te deja explorar la plataforma sin pagar.',
            },
            {
                q: '\u00bfPuedo cambiar de plan en cualquier momento?',
                a: 'Si. Puedes mejorar tu plan en cualquier momento desde tu cuenta. Si cancelas, tu plan sigue activo hasta el final del periodo que ya pagaste.',
            },
            {
                q: '\u00bfQue metodos de pago aceptan?',
                a: 'Aceptamos tarjetas de credito y debito (Visa, Mastercard, American Express) a traves de nuestra pasarela de pagos segura.',
            },
        ],
        // The answer follows what the cards show (see ivaState below).
        ivaFaq: {
            q: '\u00bfLos precios incluyen IVA?',
            a: {
                included: 'Si. Los precios mostrados incluyen IVA (16%): es el total que pagas.',
                plus: 'Los precios marcados \u00ab+ IVA\u00bb no lo incluyen: al pagar se suma el IVA (16%) y el checkout muestra el total.',
                unknown: 'El checkout cobra el total con IVA (16%) incluido.',
            },
        },
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
        subscribeCta: 'Subscribe',
        priceAtCheckout: 'Price shown at checkout',
        loadingPrice: 'Loading price…',
        perMonth: '/mo',
        compareTitle: 'Detailed comparison',
        faqTitle: 'Frequently asked questions',
        faq: [
            {
                q: 'Can I try for free before paying?',
                a: 'Not at the moment. The Free Member plan is free and lets you explore the platform without paying.',
            },
            {
                q: 'Can I change plans at any time?',
                a: 'Yes. You can upgrade at any time from your account. If you cancel, your plan stays active until the end of the period you already paid for.',
            },
            {
                q: 'What payment methods do you accept?',
                a: 'We accept credit and debit cards (Visa, Mastercard, American Express) through our secure payment gateway.',
            },
        ],
        // The answer follows what the cards show (see ivaState below).
        ivaFaq: {
            q: 'Do prices include tax?',
            a: {
                included: 'Yes. Prices shown include VAT (IVA, 16%): that is the total you pay.',
                plus: 'Prices marked "+ VAT" do not include it: VAT (IVA, 16%) is added at checkout, which shows the total.',
                unknown: 'Checkout charges the total with VAT (IVA, 16%) included.',
            },
        },
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
        subscribeCta: 'Suscribirme',
        priceAtCheckout: 'Precio al pagar',
        loadingPrice: 'Cargando precio…',
        perMonth: '/metztli',
        compareTitle: 'Tlananamicoliztli',
        faqTitle: 'Tlatlaniliztli',
        faq: [
            {
                q: '\u00bfPuedo probar gratis antes de pagar?',
                a: 'Por ahora no hay prueba gratuita. El plan Free Member es gratis y te deja explorar la plataforma sin pagar.',
            },
            {
                q: 'Huel nicpatla notlaxtlahuil?',
                a: 'Si. Puedes mejorar tu plan en cualquier momento desde tu cuenta. Si cancelas, tu plan sigue activo hasta el final del periodo que ya pagaste.',
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
    essentials: 'early_access',
    academic: 'early_access',
    institutional: 'early_access',
};

const comingSoonLabel = {
    es: 'Próximamente',
    en: 'Coming soon',
    nah: 'Hualaz niman',
};

type TierKey = 'free_member' | 'essentials' | 'academic' | 'institutional';

/** Whether the prices on the cards include IVA: all gross, any net, or none shown. */
type IvaState = 'included' | 'plus' | 'unknown';

/** The FAQ for a language, with the IVA answer that matches the cards. */
function faqFor(c: (typeof content)[keyof typeof content], ivaState: IvaState) {
    return 'ivaFaq' in c ? [...c.faq, { q: c.ivaFaq.q, a: c.ivaFaq.a[ivaState] }] : c.faq;
}

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
    const { isAuthenticated, tier } = useAuth();
    const t = content[lang];
    const { prices, failed: pricesUnavailable } = useTezcaPrices();

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

    /** Monthly MXN price from Dhanam's catalog; undefined while loading. */
    const getPrice = (tierKey: TierKey): DisplayPrice | null | undefined => {
        if (tierKey === 'free_member') return null;
        return prices ? (prices[tierKey] ?? null) : undefined;
    };

    // Gross ("IVA incluido") once Dhanam's catalog sends it, net ("+ IVA")
    // until then. The FAQ answer says the same thing as the cards.
    const shownPrices = MONETIZATION_ENABLED
        ? tiers.map(({ key }) => getPrice(key)).filter((p): p is DisplayPrice => p != null)
        : [];
    const ivaState: IvaState =
        shownPrices.length === 0 ? 'unknown' : shownPrices.every((p) => p.ivaIncluded) ? 'included' : 'plus';

    const getCtaHref = (tierKey: TierKey) => {
        if (tierKey === 'free_member') {
            return isAuthenticated ? '/cuenta' : '/login';
        }
        return getCheckoutUrl(
            tierKey,
            undefined,
            typeof window !== 'undefined' ? window.location.href : undefined,
        );
    };

    const getCtaLabel = (tierKey: TierKey) => {
        if (tierKey === 'free_member') return t.freeMemberCta;
        return t.subscribeCta;
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
                mainEntity: faqFor(content.es, ivaState).map(item => ({
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
                                            {key !== 'free_member' ? (
                                                price ? (
                                                    <div className="flex flex-wrap items-baseline gap-1">
                                                        <span className="text-3xl font-bold">
                                                            {formatMxnCentavos(price.amount)}
                                                        </span>
                                                        <span className="text-sm text-muted-foreground">
                                                            {priceUnitLabel(`MXN${t.perMonth}`, price, lang)}
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <p className="text-sm text-muted-foreground">
                                                        {pricesUnavailable || price === null
                                                            ? t.priceAtCheckout
                                                            : t.loadingPrice}
                                                    </p>
                                                )
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
                <FaqSection faq={faqFor(t, ivaState)} title={t.faqTitle} />
            </div>
        </div>
    );
}
