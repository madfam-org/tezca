'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Card, CardContent, Badge } from '@tezca/ui';
import { ArrowRight, FileText } from 'lucide-react';
import { useLang, type Lang } from '@/components/providers/LanguageContext';
import type { LawListItem } from '@tezca/lib';

const content = {
    es: {
        title: 'Leyes Destacadas',
        subtitle: 'Leyes recientemente actualizadas en la plataforma',
        viewAll: 'Ver catálogo completo',
        articles: 'artículos',
    },
    en: {
        title: 'Featured Laws',
        subtitle: 'Recently updated laws on the platform',
        viewAll: 'View full catalog',
        articles: 'articles',
    },
    nah: {
        title: 'Tenahuatilli Tlanextīlli',
        subtitle: 'Yancuīc tenahuatilli ipan tēpōzmachiyōtl',
        viewAll: 'Xiquitta mochi amatlapalōlli',
        articles: 'tlanahuatilli',
    },
};

const TIER_LABELS: Record<Lang, Record<string, string>> = {
    es: { federal: 'Federal', state: 'Estatal', municipal: 'Municipal' },
    en: { federal: 'Federal', state: 'State', municipal: 'Municipal' },
    nah: { federal: 'Federal', state: 'Altepetl', municipal: 'Calpulli' },
};

export function FeaturedLaws() {
    const { lang } = useLang();
    const t = content[lang];
    const tierLabels = TIER_LABELS[lang];
    const [laws, setLaws] = useState<LawListItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getLaws({ sort: 'date_desc', page_size: 4 })
            .then(res => setLaws(res.results))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="grid gap-4 sm:grid-cols-2">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-28 rounded-xl bg-muted animate-pulse" />
                ))}
            </div>
        );
    }

    if (laws.length === 0) return null;

    return (
        <section>
            <div className="flex items-center justify-between mb-4 sm:mb-6">
                <div>
                    <h2 className="text-xl sm:text-2xl font-bold tracking-tight">{t.title}</h2>
                    <p className="text-sm text-muted-foreground mt-1">{t.subtitle}</p>
                </div>
                <Link
                    href="/leyes?sort=date_desc"
                    className="hidden sm:flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                    {t.viewAll}
                    <ArrowRight className="h-3.5 w-3.5" />
                </Link>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
                {laws.map((law) => (
                    <Link key={law.id} href={`/leyes/${law.id}`}>
                        <Card className="h-full transition-colors hover:border-primary/50">
                            <CardContent className="p-4 sm:p-5">
                                <div className="flex items-start gap-3">
                                    <div className="rounded-lg bg-primary/10 p-2 flex-shrink-0">
                                        <FileText className="h-4 w-4 text-primary" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <h3 className="font-medium text-sm leading-tight line-clamp-2">
                                            {law.name}
                                        </h3>
                                        <div className="flex items-center gap-2 mt-2">
                                            <Badge variant="secondary" className="text-xs">
                                                {tierLabels[law.tier ?? ''] || law.tier}
                                            </Badge>
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>

            <Link
                href="/leyes?sort=date_desc"
                className="sm:hidden flex items-center justify-center gap-1 mt-4 text-sm font-medium text-primary hover:underline"
            >
                {t.viewAll}
                <ArrowRight className="h-3.5 w-3.5" />
            </Link>
        </section>
    );
}
