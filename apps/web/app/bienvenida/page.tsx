'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Scale, ArrowRight, Mail, BookOpen } from 'lucide-react';
import { Card, CardContent, Button } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { InterestGate } from '@/components/InterestGate';
import { trackEvent } from '@/lib/analytics/posthog';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const DOMAIN_CONTENT: Record<string, { es: string; en: string; nah: string }> = {
    labor: {
        es: 'Derecho laboral mexicano',
        en: 'Mexican labor law',
        nah: 'Tequitl tlanāhuatīlli',
    },
    tax: {
        es: 'Derecho fiscal mexicano',
        en: 'Mexican tax law',
        nah: 'Tlaxtlāhuīlli tlanāhuatīlli',
    },
    criminal: {
        es: 'Derecho penal mexicano',
        en: 'Mexican criminal law',
        nah: 'Tētzacualiztli tlanāhuatīlli',
    },
    civil: {
        es: 'Derecho civil mexicano',
        en: 'Mexican civil law',
        nah: 'Altepetlanāhuatīlli',
    },
    corporate: {
        es: 'Derecho corporativo mexicano',
        en: 'Mexican corporate law',
        nah: 'Pōchtēcatl tlanāhuatīlli',
    },
    constitutional: {
        es: 'Derecho constitucional mexicano',
        en: 'Mexican constitutional law',
        nah: 'Huēyi tlanāhuatīlli',
    },
};

const content = {
    es: {
        title: 'Bienvenido a Tezca',
        subtitle: 'La plataforma abierta de leyes mexicanas. Más de 30,000 leyes federales, estatales y municipales.',
        domainPrefix: 'Especializado en: ',
        newsletterTitle: 'Recibe actualizaciones legales',
        newsletterDesc: 'Suscríbete para recibir cambios legislativos relevantes a tu práctica.',
        emailPlaceholder: 'tu@correo.com',
        subscribe: 'Suscribirme',
        subscribed: '¡Listo! Te enviaremos actualizaciones.',
        alreadySubscribed: 'Ya estás suscrito.',
        error: 'Error. Intenta de nuevo.',
        exploreLaws: 'Explorar leyes',
        searchLaws: 'Buscar legislación',
        createAccount: 'Crear cuenta gratuita',
        createAccountDesc: 'Accede a más funciones con una cuenta gratuita.',
        pricing: 'Ver planes',
        pricingDesc: 'Conoce las funciones premium que próximamente estarán disponibles.',
    },
    en: {
        title: 'Welcome to Tezca',
        subtitle: 'Mexico\'s open law platform. 30,000+ federal, state, and municipal laws.',
        domainPrefix: 'Specialized in: ',
        newsletterTitle: 'Get legal updates',
        newsletterDesc: 'Subscribe for legislative changes relevant to your practice.',
        emailPlaceholder: 'you@email.com',
        subscribe: 'Subscribe',
        subscribed: 'Done! We\'ll send you updates.',
        alreadySubscribed: 'You\'re already subscribed.',
        error: 'Error. Please try again.',
        exploreLaws: 'Explore laws',
        searchLaws: 'Search legislation',
        createAccount: 'Create free account',
        createAccountDesc: 'Get access to more features with a free account.',
        pricing: 'View plans',
        pricingDesc: 'Discover the premium features coming soon.',
    },
    nah: {
        title: 'Ximopanōlti ipan Tezca',
        subtitle: 'Mexihco tlanāhuatīlli tlahcuilōlpan.',
        domainPrefix: 'Tlanāhuatīlli: ',
        newsletterTitle: 'Xicseliti tlanāhuatīlli',
        newsletterDesc: 'Ximomachiyōti ipan yancuic tlanāhuatīlli.',
        emailPlaceholder: 'tehuatl@correo.com',
        subscribe: 'Ximomachiyōti',
        subscribed: 'Cualli omochīuh.',
        alreadySubscribed: 'Ye timomachiyōtia.',
        error: 'Ahmo omochīuh.',
        exploreLaws: 'Xictēmō tlanāhuatīlli',
        searchLaws: 'Tlatemoliztli',
        createAccount: 'Xicchīhua mocuenta',
        createAccountDesc: 'Xicahci ōcachi.',
        pricing: 'Tlaxtlāhuīlli',
        pricingDesc: 'Xicahci yancuic tlanāhuatīlli.',
    },
};

export default function BienvenidaPage() {
    const { lang } = useLang();
    const { isAuthenticated } = useAuth();
    const searchParams = useSearchParams();
    const t = content[lang];

    const utmSource = searchParams.get('utm_source') ?? '';
    const utmMedium = searchParams.get('utm_medium') ?? '';
    const utmCampaign = searchParams.get('utm_campaign') ?? '';

    const domainLabel = utmCampaign ? DOMAIN_CONTENT[utmCampaign.toLowerCase()]?.[lang] : null;

    const [email, setEmail] = useState('');
    const [newsletterStatus, setNewsletterStatus] = useState<'idle' | 'loading' | 'success' | 'already' | 'error'>('idle');
    const [showAccountCta, setShowAccountCta] = useState(false);

    useEffect(() => {
        trackEvent('funnel.landing_viewed', {
            utm_source: utmSource,
            utm_medium: utmMedium,
            utm_campaign: utmCampaign,
        });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- track once on mount
    }, []);

    const handleNewsletterSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email.trim()) return;

        setNewsletterStatus('loading');
        try {
            const res = await fetch(`${API_BASE}/newsletter/subscribe/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: email.trim(),
                    topics: utmCampaign ? [utmCampaign] : [],
                    source_page: 'bienvenida',
                }),
            });
            const data = await res.json();
            if (data.status === 'already_subscribed') {
                setNewsletterStatus('already');
            } else if (res.ok) {
                setNewsletterStatus('success');
                setShowAccountCta(true);
                setEmail('');
                trackEvent('funnel.newsletter_subscribed', {
                    utm_source: utmSource,
                    utm_campaign: utmCampaign,
                });
            } else {
                setNewsletterStatus('error');
            }
        } catch {
            setNewsletterStatus('error');
        }
    };

    const newsletterMessage =
        newsletterStatus === 'success' ? t.subscribed :
        newsletterStatus === 'already' ? t.alreadySubscribed :
        newsletterStatus === 'error' ? t.error : null;

    return (
        <div className="min-h-screen bg-background">
            {/* Hero */}
            <div className="bg-gradient-to-b from-primary/5 to-background pt-16 pb-12 text-center px-4">
                <Scale className="h-10 w-10 text-primary mx-auto mb-4" aria-hidden="true" />
                <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">{t.title}</h1>
                <p className="mt-3 text-muted-foreground max-w-xl mx-auto">{t.subtitle}</p>
                {domainLabel && (
                    <p className="mt-2 text-sm font-medium text-primary">
                        {t.domainPrefix}{domainLabel}
                    </p>
                )}
            </div>

            <div className="container mx-auto px-4 sm:px-6 max-w-2xl space-y-8 pb-16">
                {/* Newsletter signup */}
                <Card>
                    <CardContent className="p-6">
                        <div className="flex items-center gap-2 mb-2">
                            <Mail className="h-5 w-5 text-primary" aria-hidden="true" />
                            <h2 className="font-semibold text-lg">{t.newsletterTitle}</h2>
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">{t.newsletterDesc}</p>
                        <form onSubmit={handleNewsletterSubmit} className="flex gap-2">
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder={t.emailPlaceholder}
                                required
                                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
                                aria-label="Email"
                            />
                            <Button type="submit" disabled={newsletterStatus === 'loading'}>
                                {t.subscribe}
                            </Button>
                        </form>
                        {newsletterMessage && (
                            <p
                                className={`mt-2 text-sm ${newsletterStatus === 'error' ? 'text-destructive' : 'text-muted-foreground'}`}
                                role="status"
                                aria-live="polite"
                            >
                                {newsletterMessage}
                            </p>
                        )}
                    </CardContent>
                </Card>

                {/* Account CTA — shown after newsletter signup or if already subscribed */}
                {(showAccountCta || newsletterStatus === 'already') && !isAuthenticated && (
                    <Card>
                        <CardContent className="p-6 text-center">
                            <h2 className="font-semibold text-lg mb-1">{t.createAccount}</h2>
                            <p className="text-sm text-muted-foreground mb-4">{t.createAccountDesc}</p>
                            <Link href={`/login?redirect=/precios`}>
                                <Button className="gap-2">
                                    {t.createAccount}
                                    <ArrowRight className="h-4 w-4" />
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>
                )}

                {/* Quick links */}
                <div className="grid sm:grid-cols-2 gap-4">
                    <Link href="/busqueda" className="block">
                        <Card className="h-full hover:border-primary/50 transition-colors">
                            <CardContent className="p-6 flex items-start gap-3">
                                <BookOpen className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                                <div>
                                    <h3 className="font-medium">{t.searchLaws}</h3>
                                    <p className="text-sm text-muted-foreground mt-1">{t.subtitle}</p>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                    <Link href="/precios" className="block">
                        <Card className="h-full hover:border-primary/50 transition-colors">
                            <CardContent className="p-6 flex items-start gap-3">
                                <Scale className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                                <div>
                                    <h3 className="font-medium">{t.pricing}</h3>
                                    <p className="text-sm text-muted-foreground mt-1">{t.pricingDesc}</p>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                </div>

                {/* Interest gate for deeper features */}
                <InterestGate
                    variant="card"
                    featureKey={utmCampaign ? 'early_access' : 'platform_access'}
                    sourcePage="bienvenida"
                />
            </div>
        </div>
    );
}
