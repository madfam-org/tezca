'use client';

import Link from 'next/link';
import { Sparkles, ArrowRight, Search, Download, Code } from 'lucide-react';
import { Button, Card, CardContent } from '@tezca/ui';
import { useLang } from '@/components/providers/LanguageContext';
import { useAuth } from '@/components/providers/AuthContext';
import { hasPaidAccess } from '@/lib/billing';

const content = {
    es: {
        headline: 'Prueba cualquier plan gratis por 3 dias',
        cta: 'Ver planes',
        pills: ['Busqueda completa', '6 formatos de descarga', 'Acceso API'],
    },
    en: {
        headline: 'Try any plan free for 3 days',
        cta: 'View plans',
        pills: ['Full search', '6 export formats', 'API access'],
    },
    nah: {
        headline: 'Xicyeyeco tlaxtlahuilli 3 tonalli',
        cta: 'Xiquitta tlaxtlahuilli',
        pills: ['Tlatemoliztli', 'Temohuiliztli', 'API'],
    },
};

const PILL_ICONS = [Search, Download, Code];

export function ConversionBanner() {
    const { lang } = useLang();
    const { tier } = useAuth();
    const t = content[lang];

    // Don't show for paid users
    if (hasPaidAccess(tier)) return null;

    return (
        <section className="py-8">
            <Card className="border-primary/20 bg-gradient-to-r from-primary/5 via-background to-primary/5 overflow-hidden">
                <CardContent className="p-6 sm:p-8 text-center">
                    <div className="inline-flex rounded-full bg-primary/10 p-2 mb-4">
                        <Sparkles className="h-5 w-5 text-primary" />
                    </div>
                    <h2 className="text-xl sm:text-2xl font-bold mb-3">{t.headline}</h2>
                    <div className="flex flex-wrap justify-center gap-2 mb-6">
                        {t.pills.map((pill, i) => {
                            const Icon = PILL_ICONS[i];
                            return (
                                <span key={i} className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-sm text-muted-foreground">
                                    <Icon className="h-3.5 w-3.5" />
                                    {pill}
                                </span>
                            );
                        })}
                    </div>
                    <Link href="/precios">
                        <Button className="gap-2 group">
                            {t.cta}
                            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                        </Button>
                    </Link>
                </CardContent>
            </Card>
        </section>
    );
}
