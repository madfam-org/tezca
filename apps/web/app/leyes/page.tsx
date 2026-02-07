'use client';

import { useEffect, useState, useCallback } from 'react';
import type { LawListItem } from '@tezca/lib';
import LawCard from '@/components/LawCard';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useLang } from '@/components/providers/LanguageContext';
import { Pagination } from '@/components/Pagination';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@tezca/ui';
import type { Lang } from '@/components/providers/LanguageContext';
import { Suspense } from 'react';

const content = {
    es: {
        subtitle: 'Explora la legislaci\u00f3n mexicana',
        home: '\u2190 Inicio',
        lawsAvailable: 'leyes disponibles',
        browseLaws: 'Leyes',
        loading: 'Cargando leyes...',
        loadError: 'No se pudieron cargar las leyes. Intenta de nuevo.',
        retry: 'Reintentar',
        noLaws: 'No se encontraron leyes.',
        compareHint: 'Selecciona leyes con \u2611 para comparar',
        sortBy: 'Ordenar por',
    },
    en: {
        subtitle: 'Explore Mexican legislation',
        home: '\u2190 Home',
        lawsAvailable: 'laws available',
        browseLaws: 'Laws',
        loading: 'Loading laws...',
        loadError: 'Could not load laws. Please try again.',
        retry: 'Retry',
        noLaws: 'No laws found.',
        compareHint: 'Select laws with \u2611 to compare',
        sortBy: 'Sort by',
    },
    nah: {
        subtitle: 'Xictlachia in m\u0113xihcatl tenahuatilli',
        home: '\u2190 Caltenco',
        lawsAvailable: 'tenahuatilli oncah',
        browseLaws: 'Tenahuatilli',
        loading: 'Mot\u0113moa tenahuatilli...',
        loadError: 'Ahmo huel\u012Bz mot\u0113moa tenahuatilli. Xicy\u0113yec\u014Dlti occ\u0113ppa.',
        retry: 'Occ\u0113ppa',
        noLaws: 'Ahmo oncah tenahuatilli.',
        compareHint: 'Xictlap\u0113peni tenahuatilli ic \u2611 ic motlan\u0101namiqui',
        sortBy: 'Xictlalia ic',
    },
};

function getSortOptions(lang: Lang) {
    const labels: Record<Lang, Record<string, string>> = {
        es: { name_asc: 'Nombre A-Z', name_desc: 'Nombre Z-A', date_desc: 'M\u00e1s recientes', article_count: 'M\u00e1s versiones' },
        en: { name_asc: 'Name A-Z', name_desc: 'Name Z-A', date_desc: 'Most recent', article_count: 'Most versions' },
        nah: { name_asc: 'T\u014dc\u0101itl A-Z', name_desc: 'T\u014dc\u0101itl Z-A', date_desc: 'Yancu\u012Bc', article_count: 'Achi tlamantli' },
    };
    const l = labels[lang];
    return [
        { value: 'name_asc', label: l.name_asc },
        { value: 'name_desc', label: l.name_desc },
        { value: 'date_desc', label: l.date_desc },
        { value: 'article_count', label: l.article_count },
    ];
}

const PAGE_SIZE = 50;

function LawsBrowseContent() {
    const { lang } = useLang();
    const t = content[lang];
    const SORT_OPTIONS = getSortOptions(lang);
    const router = useRouter();
    const searchParams = useSearchParams();

    const jurisdictionParam = searchParams.get('jurisdiction') || '';
    const sortParam = searchParams.get('sort') || 'name_asc';
    const pageParam = parseInt(searchParams.get('page') || '1', 10);

    const [laws, setLaws] = useState<LawListItem[]>([]);
    const [totalCount, setTotalCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

    const updateUrl = useCallback((params: Record<string, string>) => {
        const sp = new URLSearchParams(searchParams.toString());
        for (const [key, value] of Object.entries(params)) {
            if (value && value !== 'name_asc' && !(key === 'page' && value === '1')) {
                sp.set(key, value);
            } else {
                sp.delete(key);
            }
        }
        const qs = sp.toString();
        router.push(`/leyes${qs ? `?${qs}` : ''}`);
    }, [searchParams, router]);

    const fetchLaws = useCallback(async () => {
        setLoading(true);
        setError(false);
        try {
            const data = await api.getLaws({
                page_size: PAGE_SIZE,
                page: pageParam,
                tier: jurisdictionParam || undefined,
                sort: sortParam,
            });
            setLaws(data.results);
            setTotalCount(data.count);
        } catch {
            setError(true);
        } finally {
            setLoading(false);
        }
    }, [jurisdictionParam, sortParam, pageParam]);

    useEffect(() => {
        fetchLaws();
    }, [fetchLaws]);

    const handleSortChange = (value: string) => {
        updateUrl({ sort: value, page: '1' });
    };

    const handlePageChange = (page: number) => {
        updateUrl({ page: String(page) });
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <div className="bg-primary text-primary-foreground shadow-xl">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-4xl font-bold mb-2">
                                Tezca
                            </h1>
                            <p className="text-xl opacity-80">
                                {t.subtitle}
                            </p>
                        </div>
                        <Link
                            href="/"
                            className="bg-primary-foreground/10 hover:bg-primary-foreground/20 px-4 py-2 rounded-lg transition-colors duration-200"
                        >
                            {t.home}
                        </Link>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {loading ? (
                    <div className="text-center py-16">
                        <div className="animate-pulse space-y-4">
                            <div className="h-8 bg-muted rounded w-48 mx-auto" />
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {[...Array(6)].map((_, i) => (
                                    <div key={i} className="h-48 rounded-xl bg-muted" />
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
                ) : (
                    <>
                        {/* Stats bar + Sort */}
                        <div className="mb-8">
                            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                                <h2 className="text-2xl font-bold text-foreground">
                                    {t.browseLaws}
                                    <span className="ml-3 text-lg font-normal text-muted-foreground">
                                        {totalCount.toLocaleString()} {t.lawsAvailable}
                                    </span>
                                </h2>
                                <div className="flex items-center gap-3">
                                    <span className="text-sm text-muted-foreground hidden sm:block">
                                        {t.compareHint}
                                    </span>
                                    <Select value={sortParam} onValueChange={handleSortChange}>
                                        <SelectTrigger className="w-[180px]">
                                            <SelectValue placeholder={t.sortBy} />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {SORT_OPTIONS.map((opt) => (
                                                <SelectItem key={opt.value} value={opt.value}>
                                                    {opt.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            {laws.length === 0 ? (
                                <p className="text-center text-muted-foreground py-12">{t.noLaws}</p>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {laws.map((law) => (
                                        <LawCard key={law.id} law={law as never} />
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <Pagination
                                currentPage={pageParam}
                                totalPages={totalPages}
                                onPageChange={handlePageChange}
                                className="mt-8"
                            />
                        )}
                    </>
                )}
            </div>
        </div>
    );
}

export default function LawsPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-pulse h-8 bg-muted rounded w-48" /></div>}>
            <LawsBrowseContent />
        </Suspense>
    );
}
