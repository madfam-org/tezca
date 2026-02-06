'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { DashboardStats } from '@/lib/types';

export function DynamicFeatures() {
    const [stats, setStats] = useState<DashboardStats | null>(null);

    useEffect(() => {
        api.getStats().then(setStats).catch(console.error);
    }, []);

    const coverage = stats?.total_coverage ?? 0;
    const totalLaws = stats?.total_laws ?? 0;
    const totalArticles = stats?.total_articles ?? 0;

    return (
        <div className="rounded-2xl border border-border bg-muted/30 p-6 sm:p-8 md:p-12">
            <div className="grid gap-6 sm:gap-8 sm:grid-cols-2 md:grid-cols-3">
                <Feature
                    icon="✨"
                    title={`${coverage}% Cobertura Legal`}
                    description={`${totalLaws.toLocaleString('es-MX')} leyes federales, estatales y municipales completamente digitalizadas`}
                />
                <Feature
                    icon="🔍"
                    title="Búsqueda Completa"
                    description={`${totalArticles.toLocaleString('es-MX')} artículos indexados con búsqueda de texto completo`}
                />
                <Feature
                    icon="📊"
                    title="98.9% Precisión"
                    description="Calidad garantizada con validación automática y sistema de calificación"
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
