'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@tezca/ui';
import { Building2, Scale, Home } from 'lucide-react';
import { api } from '@/lib/api';
import type { DashboardStats, CoverageItem } from '@tezca/lib';
import { useLang, LOCALE_MAP, type Lang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        heading: 'Cobertura por Jurisdicción',
        subtitle: 'Explora leyes federales, estatales y municipales',
        loadError: 'No se pudieron cargar las estadísticas.',
        laws: 'leyes',
        coverage: 'Cobertura',
        municipalitiesCovered: 'municipios cubiertos',
        ofMunicipalities: (total: string) => `de ${total} municipios en el país`,
        ofUniverse: (universe: string) => `de ${universe}`,
        includesNonLeg: (count: string) => `Incluye ${count} leyes de otros poderes`,
    },
    en: {
        heading: 'Coverage by Jurisdiction',
        subtitle: 'Explore federal, state, and municipal laws',
        loadError: 'Could not load statistics.',
        laws: 'laws',
        coverage: 'Coverage',
        municipalitiesCovered: 'municipalities covered',
        ofMunicipalities: (total: string) => `of ${total} municipalities in the country`,
        ofUniverse: (universe: string) => `of ${universe}`,
        includesNonLeg: (count: string) => `Includes ${count} non-legislative laws`,
    },
    nah: {
        heading: 'Tlanextīliztli Altepetl',
        subtitle: 'Xictlaixmati federal, altepetl, ihuan calpulli tenahuatilli',
        loadError: 'Ahmo huelītic in tlanextīliztli.',
        laws: 'tenahuatilli',
        coverage: 'Tlanextīliztli',
        municipalitiesCovered: 'calpulli tlanextīlli',
        ofMunicipalities: (total: string) => `ipan ${total} calpulli in tlālticpac`,
        ofUniverse: (universe: string) => `ipan ${universe}`,
        includesNonLeg: (count: string) => `Quināmiqui ${count} ahmo tenahuatīlli`,
    },
};

const jurisdictionNames: Record<Lang, Record<string, string>> = {
    es: { federal: 'Federal', state: 'Estatal', municipal: 'Municipal' },
    en: { federal: 'Federal', state: 'State', municipal: 'Municipal' },
    nah: { federal: 'Federal', state: 'Altepetl', municipal: 'Calpulli' },
};

const jurisdictionConfig = [
    {
        id: 'federal' as const,
        nameKey: 'federal',
        Icon: Scale,
        countKey: 'federal_count' as const,
        coverageKey: 'federal_coverage' as const,
        coverageField: 'federal' as const,
        colorClass: 'primary',
        gradient: 'from-primary-500 to-primary-600',
        href: '/laws?jurisdiction=federal',
    },
    {
        id: 'state' as const,
        nameKey: 'state',
        Icon: Building2,
        countKey: 'state_count' as const,
        coverageKey: 'state_coverage' as const,
        coverageField: 'state' as const,
        colorClass: 'secondary',
        gradient: 'from-secondary-500 to-secondary-600',
        href: '/laws?jurisdiction=state',
    },
    {
        id: 'municipal' as const,
        nameKey: 'municipal',
        Icon: Home,
        countKey: 'municipal_count' as const,
        coverageKey: 'municipal_coverage' as const,
        coverageField: 'municipal' as const,
        colorClass: 'accent',
        gradient: 'from-accent-500 to-accent-600',
        href: '/laws?jurisdiction=municipal',
    },
];

function CoverageDisplay({
    coverageItem,
    legacyCoverage,
    jurisdictionId,
    gradient,
    lang,
}: {
    coverageItem?: CoverageItem;
    legacyCoverage: number;
    jurisdictionId: string;
    gradient: string;
    lang: Lang;
}) {
    const t = content[lang];
    const locale = LOCALE_MAP[lang];

    // Municipal has no known universe — show descriptive text instead of percentage bar
    if (jurisdictionId === 'municipal' && coverageItem) {
        return (
            <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                    {coverageItem.cities_covered} {t.municipalitiesCovered}
                </p>
                <p className="text-xs text-muted-foreground/70">
                    {t.ofMunicipalities(coverageItem.total_municipalities?.toLocaleString(locale) ?? '0')}
                </p>
            </div>
        );
    }

    // For federal/state: show "X de Y (Z%)" with progress bar
    const percentage = coverageItem?.percentage ?? legacyCoverage;
    const universe = coverageItem?.universe;

    return (
        <div className="space-y-2">
            <div className="flex justify-between text-sm font-medium">
                <span className="text-muted-foreground">
                    {universe
                        ? t.ofUniverse(universe.toLocaleString(locale))
                        : t.coverage}
                </span>
                <span className="text-foreground">{percentage}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
                <div
                    className={`h-full rounded-full bg-gradient-to-r ${gradient} transition-all duration-500`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}

export function JurisdictionCards() {
    const { lang } = useLang();
    const t = content[lang];
    const names = jurisdictionNames[lang];
    const locale = LOCALE_MAP[lang];
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        api.getStats()
            .then(setStats)
            .catch(() => setError(true))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-10 sm:py-16">
            <div className="mb-12 text-center">
                <h2 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
                    {t.heading}
                </h2>
                <p className="mt-3 text-lg text-muted-foreground">
                    {t.subtitle}
                </p>
            </div>

            {loading ? (
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-64 rounded-xl bg-muted animate-pulse" />
                    ))}
                </div>
            ) : error ? (
                <p className="text-center text-muted-foreground">{t.loadError}</p>
            ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {jurisdictionConfig.map((jurisdiction) => {
                    const count = stats ? stats[jurisdiction.countKey] : 0;
                    const legacyCoverage = stats ? stats[jurisdiction.coverageKey] : 0;
                    const coverageItem = stats?.coverage?.[jurisdiction.coverageField];

                    return (
                        <Link
                            key={jurisdiction.id}
                            href={jurisdiction.href}
                            className="group block transition-transform hover:-translate-y-1"
                        >
                            <Card className="relative h-full overflow-hidden border-2 transition-all hover:border-primary-300 hover:shadow-lg">
                                {/* Background gradient */}
                                <div className={`absolute inset-0 bg-gradient-to-br ${jurisdiction.gradient} opacity-5`} />

                                <CardContent className="relative p-5 sm:p-8">
                                    {/* Icon */}
                                    <div className={`mb-6 inline-flex rounded-xl bg-gradient-to-br ${jurisdiction.gradient} p-4 shadow-lg`}>
                                        <jurisdiction.Icon className="h-10 w-10 text-white" />
                                    </div>

                                    {/* Name */}
                                    <h3 className="font-display text-2xl font-bold text-foreground mb-4">
                                        {names[jurisdiction.nameKey]}
                                    </h3>

                                    {/* Stats */}
                                    <div className="space-y-4">
                                        <div className="flex items-baseline gap-3">
                                            <span className="font-display text-4xl font-bold text-foreground">
                                                {count.toLocaleString(locale)}
                                            </span>
                                            <span className="text-base text-muted-foreground">{t.laws}</span>
                                        </div>

                                        {/* Non-legislative sub-line for state */}
                                        {jurisdiction.id === 'state' && stats?.non_legislative_count != null && stats.non_legislative_count > 0 && (
                                            <p className="text-xs text-muted-foreground">
                                                {t.includesNonLeg(stats.non_legislative_count.toLocaleString(locale))}
                                            </p>
                                        )}

                                        {/* Coverage display */}
                                        <CoverageDisplay
                                            coverageItem={coverageItem}
                                            legacyCoverage={legacyCoverage}
                                            jurisdictionId={jurisdiction.id}
                                            gradient={jurisdiction.gradient}
                                            lang={lang}
                                        />
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    );
                })}
            </div>
            )}
        </div>
    );
}
