'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@tezca/ui';
import { api } from '@/lib/api';
import { useLang, type Lang } from '@/components/providers/LanguageContext';

const content: Record<Lang, {
    heading: string;
    subtitle: string;
    laws: string;
    viewLaws: string;
    backToStates: string;
    loading: string;
    loadError: string;
    retry: string;
    noStates: string;
    stateCount: string;
}> = {
    es: {
        heading: 'Estados de M\u00e9xico',
        subtitle: 'Explora leyes por estado',
        laws: 'leyes',
        viewLaws: 'Ver leyes',
        backToStates: '\u2190 Todos los estados',
        loading: 'Cargando estados...',
        loadError: 'No se pudieron cargar los estados. Intenta de nuevo.',
        retry: 'Reintentar',
        noStates: 'No se encontraron estados.',
        stateCount: 'estados',
    },
    en: {
        heading: 'States of Mexico',
        subtitle: 'Browse laws by state',
        laws: 'laws',
        viewLaws: 'View laws',
        backToStates: '\u2190 All states',
        loading: 'Loading states...',
        loadError: 'Could not load states. Please try again.',
        retry: 'Retry',
        noStates: 'No states found.',
        stateCount: 'states',
    },
    nah: {
        heading: 'Altepetl M\u0113xihco',
        subtitle: 'Xictlaixmati tenahuatilli ic altepetl',
        laws: 'tenahuatilli',
        viewLaws: 'Xiquitta tenahuatilli',
        backToStates: '\u2190 Mochi altepetl',
        loading: 'Mot\u0113moa altepetl...',
        loadError: 'Ahmo huel\u012bz mot\u0113moa altepetl. Xicy\u0113yec\u014dlti occ\u0113ppa.',
        retry: 'Occ\u0113ppa',
        noStates: 'Ahmo oncah altepetl.',
        stateCount: 'altepetl',
    },
};

export function StatesGrid() {
    const { lang } = useLang();
    const t = content[lang];

    const [states, setStates] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const fetchStates = useCallback(async () => {
        setLoading(true);
        setError(false);
        try {
            const data = await api.getStates();
            setStates(data.states);
        } catch {
            setError(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStates();
    }, [fetchStates]);

    return (
        <div className="min-h-screen bg-background">
            {/* Hero header */}
            <div className="bg-primary text-primary-foreground shadow-xl">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                        <div>
                            <h1 className="text-2xl sm:text-4xl font-bold mb-2">
                                {t.heading}
                            </h1>
                            <p className="text-xl opacity-80">
                                {t.subtitle}
                            </p>
                        </div>
                        <Link
                            href="/"
                            className="bg-primary-foreground/10 hover:bg-primary-foreground/20 px-4 py-2 rounded-lg transition-colors duration-200"
                        >
                            {lang === 'es' ? '\u2190 Inicio' : lang === 'en' ? '\u2190 Home' : '\u2190 Caltenco'}
                        </Link>
                    </div>
                </div>
            </div>

            {/* Content area */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {loading ? (
                    <div className="text-center py-16">
                        <div className="animate-pulse space-y-4">
                            <div className="h-8 bg-muted rounded w-48 mx-auto" />
                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                                {[...Array(12)].map((_, i) => (
                                    <div key={i} className="h-28 rounded-xl bg-muted" />
                                ))}
                            </div>
                        </div>
                        <p className="text-muted-foreground mt-4">{t.loading}</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-16">
                        <p className="text-destructive mb-4">{t.loadError}</p>
                        <button
                            onClick={fetchStates}
                            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                        >
                            {t.retry}
                        </button>
                    </div>
                ) : states.length === 0 ? (
                    <p className="text-center text-muted-foreground py-12">{t.noStates}</p>
                ) : (
                    <>
                        <p className="text-sm text-muted-foreground mb-6">
                            {states.length} {t.stateCount}
                        </p>

                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-4 gap-4">
                            {states.map((state) => (
                                <Link
                                    key={state}
                                    href={`/estados/${encodeURIComponent(state)}`}
                                    className="group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl"
                                >
                                    <Card className="h-full transition-all duration-200 group-hover:shadow-lg group-hover:border-primary/50 group-hover:-translate-y-0.5">
                                        <CardContent className="flex flex-col items-center justify-center p-6 text-center">
                                            <h2 className="text-base font-semibold text-foreground mb-2 truncate group-hover:text-primary transition-colors">
                                                {state}
                                            </h2>
                                            <span className="text-xs text-muted-foreground">
                                                {t.viewLaws}
                                            </span>
                                        </CardContent>
                                    </Card>
                                </Link>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
