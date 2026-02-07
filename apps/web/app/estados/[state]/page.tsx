'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { Card, CardContent, Badge } from '@tezca/ui';
import { api } from '@/lib/api';
import { useLang, type Lang } from '@/components/providers/LanguageContext';
import type { LawListItem } from '@tezca/lib';

const PAGE_SIZE = 50;

const content: Record<Lang, {
    backToStates: string;
    laws: string;
    loading: string;
    loadError: string;
    retry: string;
    noLaws: string;
    page: string;
    of: string;
    previous: string;
    next: string;
    viewLaw: string;
    versions: string;
}> = {
    es: {
        backToStates: '\u2190 Todos los estados',
        laws: 'leyes',
        loading: 'Cargando leyes...',
        loadError: 'No se pudieron cargar las leyes. Intenta de nuevo.',
        retry: 'Reintentar',
        noLaws: 'No se encontraron leyes para este estado.',
        page: 'P\u00e1gina',
        of: 'de',
        previous: 'Anterior',
        next: 'Siguiente',
        viewLaw: 'Ver ley',
        versions: 'versiones',
    },
    en: {
        backToStates: '\u2190 All states',
        laws: 'laws',
        loading: 'Loading laws...',
        loadError: 'Could not load laws. Please try again.',
        retry: 'Retry',
        noLaws: 'No laws found for this state.',
        page: 'Page',
        of: 'of',
        previous: 'Previous',
        next: 'Next',
        viewLaw: 'View law',
        versions: 'versions',
    },
    nah: {
        backToStates: '\u2190 Mochi altepetl',
        laws: 'tenahuatilli',
        loading: 'Mot\u0113moa tenahuatilli...',
        loadError: 'Ahmo huel\u012bz mot\u0113moa tenahuatilli. Xicy\u0113yec\u014dlti occ\u0113ppa.',
        retry: 'Occ\u0113ppa',
        noLaws: 'Ahmo oncah tenahuatilli ic n\u012bn altepetl.',
        page: 'Amatl',
        of: 'ic',
        previous: 'Achto',
        next: 'Niman',
        viewLaw: 'Xiquitta tenahuatilli',
        versions: 'tlamantli',
    },
};

/** Map tier values to display labels per language */
const tierLabels: Record<string, Record<Lang, string>> = {
    federal: { es: 'Federal', en: 'Federal', nah: 'Cemanahuac' },
    state: { es: 'Estatal', en: 'State', nah: 'Altepetl' },
    municipal: { es: 'Municipal', en: 'Municipal', nah: 'Calpulli' },
};

export default function StateLawsPage() {
    const params = useParams<{ state: string }>();
    const searchParams = useSearchParams();
    const { lang } = useLang();
    const t = content[lang];

    const stateName = decodeURIComponent(params.state);
    const currentPage = Number(searchParams.get('page')) || 1;

    const [laws, setLaws] = useState<LawListItem[]>([]);
    const [totalCount, setTotalCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

    const fetchLaws = useCallback(async () => {
        setLoading(true);
        setError(false);
        try {
            const data = await api.getLaws({
                state: stateName,
                page: currentPage,
                page_size: PAGE_SIZE,
            });
            setLaws(data.results);
            setTotalCount(data.count);
        } catch {
            setError(true);
        } finally {
            setLoading(false);
        }
    }, [stateName, currentPage]);

    useEffect(() => {
        fetchLaws();
    }, [fetchLaws]);

    return (
        <div className="min-h-screen bg-background">
            {/* Hero header */}
            <div className="bg-primary text-primary-foreground shadow-xl">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-4xl font-bold mb-2">
                                {stateName}
                            </h1>
                            {!loading && !error && (
                                <p className="text-xl opacity-80">
                                    {totalCount} {t.laws}
                                </p>
                            )}
                        </div>
                        <Link
                            href="/estados"
                            className="bg-primary-foreground/10 hover:bg-primary-foreground/20 px-4 py-2 rounded-lg transition-colors duration-200"
                        >
                            {t.backToStates}
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
                            <div className="space-y-4">
                                {[...Array(6)].map((_, i) => (
                                    <div key={i} className="h-24 rounded-xl bg-muted" />
                                ))}
                            </div>
                        </div>
                        <p className="text-muted-foreground mt-4">{t.loading}</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-16">
                        <p className="text-destructive mb-4">{t.loadError}</p>
                        <button
                            onClick={fetchLaws}
                            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                        >
                            {t.retry}
                        </button>
                    </div>
                ) : laws.length === 0 ? (
                    <p className="text-center text-muted-foreground py-12">{t.noLaws}</p>
                ) : (
                    <>
                        {/* Law list */}
                        <div className="space-y-4">
                            {laws.map((law) => (
                                <Link
                                    key={law.id}
                                    href={`/laws/${law.id}`}
                                    className="block group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl"
                                >
                                    <Card className="transition-all duration-200 group-hover:shadow-lg group-hover:border-primary/50">
                                        <CardContent className="p-5">
                                            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                                                <div className="flex-1 min-w-0">
                                                    <h2 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-2">
                                                        {law.name}
                                                    </h2>
                                                    <div className="flex flex-wrap gap-2 mt-2">
                                                        {law.tier && (
                                                            <Badge variant="secondary">
                                                                {tierLabels[law.tier]?.[lang] ?? law.tier}
                                                            </Badge>
                                                        )}
                                                        {law.law_type && (
                                                            <Badge variant="outline">
                                                                {law.law_type}
                                                            </Badge>
                                                        )}
                                                        {law.category && (
                                                            <Badge variant="outline">
                                                                {law.category}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    {law.versions != null && law.versions > 0 && (
                                                        <p className="text-xs text-muted-foreground mt-2">
                                                            {law.versions} {t.versions}
                                                        </p>
                                                    )}
                                                </div>
                                                <span className="text-xs text-muted-foreground shrink-0 self-center hidden sm:block">
                                                    {t.viewLaw} &rarr;
                                                </span>
                                            </div>
                                        </CardContent>
                                    </Card>
                                </Link>
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <nav
                                aria-label={lang === 'es' ? 'Paginaci\u00f3n' : lang === 'en' ? 'Pagination' : 'Tlapoalli'}
                                className="flex items-center justify-center gap-4 mt-8"
                            >
                                {currentPage > 1 ? (
                                    <Link
                                        href={`/estados/${encodeURIComponent(stateName)}?page=${currentPage - 1}`}
                                        className="px-4 py-2 rounded-lg bg-muted text-foreground hover:bg-muted/80 transition-colors text-sm font-medium"
                                    >
                                        {t.previous}
                                    </Link>
                                ) : (
                                    <span className="px-4 py-2 rounded-lg bg-muted/50 text-muted-foreground text-sm font-medium cursor-not-allowed">
                                        {t.previous}
                                    </span>
                                )}

                                <span className="text-sm text-muted-foreground">
                                    {t.page} {currentPage} {t.of} {totalPages}
                                </span>

                                {currentPage < totalPages ? (
                                    <Link
                                        href={`/estados/${encodeURIComponent(stateName)}?page=${currentPage + 1}`}
                                        className="px-4 py-2 rounded-lg bg-muted text-foreground hover:bg-muted/80 transition-colors text-sm font-medium"
                                    >
                                        {t.next}
                                    </Link>
                                ) : (
                                    <span className="px-4 py-2 rounded-lg bg-muted/50 text-muted-foreground text-sm font-medium cursor-not-allowed">
                                        {t.next}
                                    </span>
                                )}
                            </nav>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
