'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, Badge } from '@tezca/ui';
import { api } from '@/lib/api';
import { useLang, type Lang } from '@/components/providers/LanguageContext';
import type { RelatedLaw } from '@tezca/lib';

const content = {
    es: {
        title: 'Leyes Relacionadas',
        loading: 'Buscando leyes relacionadas...',
        empty: 'No se encontraron leyes relacionadas.',
    },
    en: {
        title: 'Related Laws',
        loading: 'Finding related laws...',
        empty: 'No related laws found.',
    },
    nah: {
        title: 'Tenahuatilli Inehuan',
        loading: 'Motemohua tenahuatilli inehuan...',
        empty: 'Ahmo oncah tenahuatilli inehuan.',
    },
};

function tierLabel(tier: string, lang: Lang): string {
    const labels: Record<Lang, Record<string, string>> = {
        es: { federal: 'Federal', state: 'Estatal', municipal: 'Municipal' },
        en: { federal: 'Federal', state: 'State', municipal: 'Municipal' },
        nah: { federal: 'Federal', state: 'Altepetl', municipal: 'Calpulli' },
    };
    return labels[lang][tier] || tier;
}

interface RelatedLawsProps {
    lawId: string;
}

export function RelatedLaws({ lawId }: RelatedLawsProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [related, setRelated] = useState<RelatedLaw[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        api.getRelatedLaws(lawId)
            .then((data) => {
                if (!cancelled) setRelated(data.related || []);
            })
            .catch(() => {
                if (!cancelled) setRelated([]);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, [lawId]);

    if (loading) {
        return (
            <div className="mt-8">
                <h2 className="text-lg font-semibold mb-4">{t.title}</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    if (related.length === 0) return null;

    return (
        <section className="mt-8" aria-label={t.title}>
            <h2 className="text-lg font-semibold mb-4">{t.title}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {related.map((law) => (
                    <Link key={law.law_id} href={`/leyes/${law.law_id}`} className="block group">
                        <Card className="h-full transition-all hover:shadow-md hover:border-primary/30">
                            <CardContent className="p-4">
                                <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors line-clamp-2">
                                    {law.name}
                                </p>
                                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                                    {law.tier && (
                                        <Badge variant="outline" className="text-xs capitalize">
                                            {tierLabel(law.tier, lang)}
                                        </Badge>
                                    )}
                                    {law.category && (
                                        <Badge variant="secondary" className="text-xs capitalize">
                                            {law.category}
                                        </Badge>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}
            </div>
        </section>
    );
}
