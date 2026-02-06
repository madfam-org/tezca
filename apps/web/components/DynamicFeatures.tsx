'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { DashboardStats } from '@/lib/types';

export function DynamicFeatures() {
    const [stats, setStats] = useState<DashboardStats | null>(null);

    useEffect(() => {
        api.getStats().then(setStats).catch(console.error);
    }, []);

    const coverage = stats?.coverage?.leyes_vigentes;
    const totalArticles = stats?.total_articles ?? 0;

    // Use coverage breakdown if available, fall back to legacy fields
    const coverageLabel = coverage
        ? `${coverage.count.toLocaleString('es-MX')} de ${coverage.universe?.toLocaleString('es-MX')} leyes vigentes (${coverage.percentage}%)`
        : `${(stats?.total_laws ?? 0).toLocaleString('es-MX')} leyes digitalizadas`;

    return (
        <div className="rounded-2xl border border-border bg-muted/30 p-6 sm:p-8 md:p-12">
            <div className="grid gap-6 sm:gap-8 sm:grid-cols-2 md:grid-cols-3">
                <Feature
                    icon="✨"
                    title={coverage ? `${coverage.percentage}% Cobertura Legislativa` : 'Cobertura Legal'}
                    description={coverageLabel}
                />
                <Feature
                    icon="🔍"
                    title="Búsqueda Completa"
                    description={`${totalArticles.toLocaleString('es-MX')} artículos indexados con búsqueda de texto completo`}
                />
                <Feature
                    icon="🏛️"
                    title="32 Estados Cubiertos"
                    description="Legislación de todas las entidades federativas del país"
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
