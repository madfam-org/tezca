'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Building2, Scale, Home } from 'lucide-react';
import { api } from '@/lib/api';
import type { DashboardStats, CoverageItem } from '@/lib/types';

const jurisdictionConfig = [
    {
        id: 'federal' as const,
        name: 'Federal',
        Icon: Scale,
        countKey: 'federal_count' as const,
        coverageKey: 'federal_coverage' as const,
        coverageField: 'federal' as const,
        colorClass: 'primary',
        gradient: 'from-primary-500 to-primary-600',
        href: '/laws/federal',
    },
    {
        id: 'state' as const,
        name: 'Estatal',
        Icon: Building2,
        countKey: 'state_count' as const,
        coverageKey: 'state_coverage' as const,
        coverageField: 'state' as const,
        colorClass: 'secondary',
        gradient: 'from-secondary-500 to-secondary-600',
        href: '/laws/state',
    },
    {
        id: 'municipal' as const,
        name: 'Municipal',
        Icon: Home,
        countKey: 'municipal_count' as const,
        coverageKey: 'municipal_coverage' as const,
        coverageField: 'municipal' as const,
        colorClass: 'accent',
        gradient: 'from-accent-500 to-accent-600',
        href: '/laws/municipal',
    },
];

function CoverageDisplay({
    coverageItem,
    legacyCoverage,
    jurisdictionId,
    gradient,
}: {
    coverageItem?: CoverageItem;
    legacyCoverage: number;
    jurisdictionId: string;
    gradient: string;
}) {
    // Municipal has no known universe — show descriptive text instead of percentage bar
    if (jurisdictionId === 'municipal' && coverageItem) {
        return (
            <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                    {coverageItem.cities_covered} municipios cubiertos
                </p>
                <p className="text-xs text-muted-foreground/70">
                    de {coverageItem.total_municipalities?.toLocaleString('es-MX')} municipios en el país
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
                        ? `de ${universe.toLocaleString('es-MX')}`
                        : 'Cobertura'}
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
    const [stats, setStats] = useState<DashboardStats | null>(null);

    useEffect(() => {
        api.getStats().then(setStats).catch(console.error);
    }, []);

    return (
        <div className="mx-auto max-w-7xl px-6 py-16">
            <div className="mb-12 text-center">
                <h2 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
                    Cobertura por Jurisdicción
                </h2>
                <p className="mt-3 text-lg text-muted-foreground">
                    Explora leyes federales, estatales y municipales
                </p>
            </div>

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

                                <CardContent className="relative p-8">
                                    {/* Icon */}
                                    <div className={`mb-6 inline-flex rounded-xl bg-gradient-to-br ${jurisdiction.gradient} p-4 shadow-lg`}>
                                        <jurisdiction.Icon className="h-10 w-10 text-white" />
                                    </div>

                                    {/* Name */}
                                    <h3 className="font-display text-2xl font-bold text-foreground mb-4">
                                        {jurisdiction.name}
                                    </h3>

                                    {/* Stats */}
                                    <div className="space-y-4">
                                        <div className="flex items-baseline gap-3">
                                            <span className="font-display text-4xl font-bold text-foreground">
                                                {count.toLocaleString('es-MX')}
                                            </span>
                                            <span className="text-base text-muted-foreground">leyes</span>
                                        </div>

                                        {/* Coverage display */}
                                        <CoverageDisplay
                                            coverageItem={coverageItem}
                                            legacyCoverage={legacyCoverage}
                                            jurisdictionId={jurisdiction.id}
                                            gradient={jurisdiction.gradient}
                                        />
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
