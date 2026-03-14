'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { DashboardStats } from '@tezca/lib';
import { useLang, LOCALE_MAP } from '@/components/providers/LanguageContext';

const content = {
    es: {
        coverageFallback: 'Cobertura Legal',
        coverageWithPct: (pct: number) => `${pct}% Cobertura Legislativa`,
        coverageDesc: (count: string, universe: string, pct: number) =>
            `${count} de ${universe} leyes vigentes (${pct}%)`,
        coverageDescFallback: (count: string) => `${count} leyes digitalizadas`,
        searchTitle: 'Búsqueda Completa',
        searchDesc: (n: string) => `${n} artículos indexados con búsqueda de texto completo`,
        statesTitle: '32 Estados Cubiertos',
        statesDesc: 'Legislación de todas las entidades federativas del país',
    },
    en: {
        coverageFallback: 'Legal Coverage',
        coverageWithPct: (pct: number) => `${pct}% Legislative Coverage`,
        coverageDesc: (count: string, universe: string, pct: number) =>
            `${count} of ${universe} active laws (${pct}%)`,
        coverageDescFallback: (count: string) => `${count} digitized laws`,
        searchTitle: 'Full-Text Search',
        searchDesc: (n: string) => `${n} articles indexed with full-text search`,
        statesTitle: '32 States Covered',
        statesDesc: 'Legislation from all states in the country',
    },
    nah: {
        coverageFallback: 'Tenahuatiliz Tlanextīliztli',
        coverageWithPct: (pct: number) => `${pct}% Tenahuatiliz Tlanextīliztli`,
        coverageDesc: (count: string, universe: string, pct: number) =>
            `${count} ipan ${universe} tenahuatilli (${pct}%)`,
        coverageDescFallback: (count: string) => `${count} tenahuatilli tēpōzmachiyōtīlli`,
        searchTitle: 'Mochi Tlahcuilōlli Tlatemoliztli',
        searchDesc: (n: string) => `${n} tlanahuatilli tlatemoliztli`,
        statesTitle: '32 Altepetl',
        statesDesc: 'Tenahuatilli mochi altepetl in tlālticpac',
    },
};

export function DynamicFeatures() {
    const { lang } = useLang();
    const t = content[lang];
    const locale = LOCALE_MAP[lang];
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getStats()
            .then(setStats)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="rounded-2xl border border-border bg-muted/30 p-6 sm:p-8 md:p-12">
                <div className="grid gap-6 sm:gap-8 sm:grid-cols-2 md:grid-cols-3">
                    {[0, 1, 2].map((i) => (
                        <div key={i} className="text-center animate-pulse">
                            <div className="mb-3 sm:mb-4 h-10 w-10 rounded-full bg-muted mx-auto" />
                            <div className="h-5 bg-muted rounded w-3/4 mx-auto mb-2" />
                            <div className="h-4 bg-muted rounded w-full mx-auto" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    const coverage = stats?.coverage?.leyes_vigentes;
    const totalArticles = stats?.total_articles ?? 0;

    const clampedPct = coverage ? Math.min(coverage.percentage ?? 0, 100) : 0;
    const displayUniverse = coverage
        ? Math.max(coverage.count, coverage.universe ?? 0)
        : 0;

    const coverageLabel = coverage
        ? t.coverageDesc(
            coverage.count.toLocaleString(locale),
            displayUniverse.toLocaleString(locale),
            clampedPct
          )
        : t.coverageDescFallback((stats?.total_laws ?? 0).toLocaleString(locale));

    return (
        <div className="rounded-2xl border border-border bg-muted/30 p-6 sm:p-8 md:p-12">
            <div className="grid gap-6 sm:gap-8 sm:grid-cols-2 md:grid-cols-3">
                <Feature
                    icon="✨"
                    title={coverage ? t.coverageWithPct(clampedPct) : t.coverageFallback}
                    description={coverageLabel}
                />
                <Feature
                    icon="🔍"
                    title={t.searchTitle}
                    description={t.searchDesc(totalArticles.toLocaleString(locale))}
                />
                <Feature
                    icon="🏛️"
                    title={t.statesTitle}
                    description={t.statesDesc}
                />
            </div>
        </div>
    );
}

function Feature({ icon, title, description }: { icon: string; title: string; description: string }) {
    return (
        <div className="text-center">
            <div className="mb-3 sm:mb-4 text-3xl sm:text-4xl">{icon}</div>
            <h3 className="font-display text-base sm:text-lg font-bold text-foreground mb-1 sm:mb-2">{title}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
        </div>
    );
}
