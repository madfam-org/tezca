'use client';

import Link from 'next/link';
import { ArrowRight, Code2 } from 'lucide-react';
import { Button, Card, CardContent } from '@tezca/ui';
import { useAuth } from '@/components/providers/AuthContext';
import { useLang } from '@/components/providers/LanguageContext';
import { hasPaidAccess } from '@/lib/billing';
import { trackEvent } from '@/lib/analytics/posthog';

const content = {
    es: {
        title: 'Obtén acceso a la API',
        body: 'Desde búsqueda hasta webhooks, Tezca tiene un plan para ti.',
        cta: 'Ver planes',
    },
    en: {
        title: 'Get API access',
        body: 'From search to webhooks, Tezca has a plan for you.',
        cta: 'View plans',
    },
    nah: {
        title: 'Xicseliti API',
        body: 'Tlatemoliztli ihuan webhooks, Tezca quipiya motlaxtlahuil.',
        cta: 'Xiquitta tlaxtlahuilli',
    },
};

export function DevApiCta() {
    const { isAuthenticated, tier } = useAuth();
    const { lang } = useLang();
    const t = content[lang];

    if (hasPaidAccess(tier)) return null;

    const ctaHref = isAuthenticated ? '/precios' : '/login?redirect=/precios';

    return (
        <section className="mt-14 sm:mt-20 pt-12 border-t border-border">
            <Card className="border-primary/20 bg-gradient-to-r from-primary/5 via-background to-primary/5">
                <CardContent className="p-6 sm:p-8 flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
                    <div className="rounded-full bg-primary/10 p-3 shrink-0">
                        <Code2 className="h-6 w-6 text-primary" />
                    </div>
                    <div className="flex-1 text-center sm:text-left">
                        <h3 className="font-bold text-lg">{t.title}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">{t.body}</p>
                    </div>
                    <Link
                        href={ctaHref}
                        onClick={() => trackEvent('dev_docs.cta_clicked', { tier })}
                    >
                        <Button className="gap-2 group shrink-0">
                            {t.cta}
                            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                        </Button>
                    </Link>
                </CardContent>
            </Card>
        </section>
    );
}
