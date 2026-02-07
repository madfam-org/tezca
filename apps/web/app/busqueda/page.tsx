'use client';

import { useState, useEffect } from 'react';
import DOMPurify from 'isomorphic-dompurify';
import { Search as SearchIcon, Loader2, Filter as FilterIcon, Link2, Check } from 'lucide-react';
import { SearchResultsSkeleton } from '@/components/skeletons/SearchResultsSkeleton';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, Card, CardContent, Badge } from "@tezca/ui";
import { SearchFilters, type SearchFilterState } from '@/components/SearchFilters';
import { SearchAutocomplete } from '@/components/SearchAutocomplete';
import { Pagination } from '@/components/Pagination';
import { api } from '@/lib/api';
import { useLang } from '@/components/providers/LanguageContext';
import type { SearchResult, FacetBucket } from "@tezca/lib";

const content = {
    es: {
        searchError: 'Error al buscar',
        pageTitle: 'Buscar Leyes',
        searchPlaceholder: 'Buscar por artículo, título, contenido...',
        searchButton: 'Buscar',
        hideFilters: 'Ocultar Filtros',
        showFilters: 'Mostrar Filtros',
        results: 'resultados',
        noResultsFor: 'No se encontraron resultados para',
        tryDifferent: 'Intenta con otros términos de búsqueda o ajusta los filtros',
        suggestions: 'Sugerencias:',
        enterSearchTerm: 'Ingresa un término de búsqueda para comenzar',
        showing: 'Mostrando',
        of: 'de',
        result: 'resultado',
        resultPlural: 'resultados',
        page: 'Página',
        pageOf: 'de',
        published: 'Publicación:',
        relevance: 'Relevancia',
        dateLocale: 'es-MX' as const,
        shareSearch: 'Compartir búsqueda',
        copied: '¡Copiado!',
        removeFilter: 'Quitar filtro:',
    },
    en: {
        searchError: 'Search error',
        pageTitle: 'Search Laws',
        searchPlaceholder: 'Search by article, title, content...',
        searchButton: 'Search',
        hideFilters: 'Hide Filters',
        showFilters: 'Show Filters',
        results: 'results',
        noResultsFor: 'No results found for',
        tryDifferent: 'Try different search terms or adjust filters',
        suggestions: 'Suggestions:',
        enterSearchTerm: 'Enter a search term to get started',
        showing: 'Showing',
        of: 'of',
        result: 'result',
        resultPlural: 'results',
        page: 'Page',
        pageOf: 'of',
        published: 'Published:',
        relevance: 'Relevance',
        dateLocale: 'en-US' as const,
        shareSearch: 'Share search',
        copied: 'Copied!',
        removeFilter: 'Remove filter:',
    },
    nah: {
        searchError: 'Tlatemoliztli tlahtlac\u014Dlli',
        pageTitle: 'Tlatemoliztli Tenahuatilli',
        searchPlaceholder: 'Xict\u0113moa ic tlanahuatilli, t\u014Dc\u0101itl, tlamachiliztli...',
        searchButton: 'Tlatemoliztli',
        hideFilters: 'Xictl\u0101tia Tlapepenilistli',
        showFilters: 'Xicnextia Tlapepenilistli',
        results: 'tlanext\u012Bliztli',
        noResultsFor: 'Ahmo oncah tlanext\u012Bliztli ic',
        tryDifferent: 'Xicy\u0113yec\u014Dlti occ\u0113 tlatemoliztli ahno\u0304zo xicpátia tlapepenilistli',
        suggestions: 'Tlan\u014Dn\u014Dtzaliztli:',
        enterSearchTerm: 'Xictl\u0101lia c\u0113 tlatemoliztli ic motlaht\u014Dltia',
        showing: 'Monextia',
        of: 'ic',
        result: 'tlanext\u012Bliztli',
        resultPlural: 'tlanext\u012Bliztli',
        page: '\u0100moxihuitl',
        pageOf: 'ic',
        published: 'T\u014Dnalli:',
        relevance: 'Tlan\u0101huatilli',
        dateLocale: 'es-MX' as const,
        shareSearch: 'Xict\u0113maca tlatemoliztli',
        copied: '\u014Cmot\u0113cac!',
        removeFilter: 'Xicpohua:',
    },
};

const DEFAULT_FILTERS: SearchFilterState = {
    jurisdiction: ['federal'],
    category: null,
    state: null,
    municipality: null,
    status: 'all',
    law_type: 'all',
    sort: 'relevance',
    title: '',
    chapter: '',
};

const PAGE_SIZE = 10;

import { Suspense } from 'react';

function SearchContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const initialQuery = searchParams?.get('q') || '';
    const [showFilters, setShowFilters] = useState(false);
    const { lang } = useLang();
    const t = content[lang];


    const [query, setQuery] = useState(initialQuery);
    const [filters, setFilters] = useState<SearchFilterState>({
        ...DEFAULT_FILTERS,
        jurisdiction: searchParams?.get('jurisdiction')?.split(',') || DEFAULT_FILTERS.jurisdiction,
        category: searchParams?.get('category') || DEFAULT_FILTERS.category,
        state: searchParams?.get('state') || DEFAULT_FILTERS.state,
        municipality: searchParams?.get('municipality') || DEFAULT_FILTERS.municipality,
        status: searchParams?.get('status') || DEFAULT_FILTERS.status,
        law_type: searchParams?.get('law_type') || DEFAULT_FILTERS.law_type,
        sort: searchParams?.get('sort') || DEFAULT_FILTERS.sort,
        date_range: searchParams?.get('date_range') || DEFAULT_FILTERS.date_range,
        title: searchParams?.get('title') || DEFAULT_FILTERS.title,
        chapter: searchParams?.get('chapter') || DEFAULT_FILTERS.chapter,
    });
    const [currentPage, setCurrentPage] = useState(
        parseInt(searchParams?.get('page') || '1', 10)
    );
    const [results, setResults] = useState<SearchResult[]>([]);
    const [total, setTotal] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [shareCopied, setShareCopied] = useState(false);
    const [facets, setFacets] = useState<Record<string, FacetBucket[]> | undefined>(undefined);

    const buildSearchParams = (q: string, f: SearchFilterState, page: number) => {
        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (f.jurisdiction.length) params.set('jurisdiction', f.jurisdiction.join(','));
        if (f.category) params.set('category', f.category);
        if (f.state) params.set('state', f.state);
        if (f.municipality) params.set('municipality', f.municipality);
        if (f.status !== 'all') params.set('status', f.status);
        if (f.law_type && f.law_type !== 'all') params.set('law_type', f.law_type);
        if (f.sort !== 'relevance') params.set('sort', f.sort);
        if (f.date_range) params.set('date_range', f.date_range);
        if (f.title) params.set('title', f.title);
        if (f.chapter) params.set('chapter', f.chapter);
        if (page > 1) params.set('page', String(page));
        return params;
    };

    // Perform search on initial load from URL params
    useEffect(() => {
        if (initialQuery) {
            performSearch(initialQuery, filters, currentPage);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally only runs on initialQuery change (URL-driven)
    }, [initialQuery]);

    const performSearch = async (
        searchQuery: string,
        searchFilters: SearchFilterState,
        page: number
    ) => {
        if (!searchQuery.trim()) {
            setResults([]);
            setTotal(0);
            setTotalPages(0);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const data = await api.search(searchQuery, {
                jurisdiction: searchFilters.jurisdiction,
                category: searchFilters.category,
                state: searchFilters.state,
                municipality: searchFilters.municipality,
                status: searchFilters.status,
                law_type: searchFilters.law_type,
                sort: searchFilters.sort,
                date_range: searchFilters.date_range,
                title: searchFilters.title,
                chapter: searchFilters.chapter,
                page,
                page_size: PAGE_SIZE,
            });

            setResults(data.results || []);
            setTotal(data.total || data.results.length);
            setTotalPages(data.total_pages || Math.ceil((data.total || data.results.length) / PAGE_SIZE));
            setFacets(data.facets);

            if (data.warning) {
                setError(data.warning);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : t.searchError);
            setResults([]);
            setTotal(0);
            setTotalPages(0);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmitQuery = (q: string) => {
        if (q.trim()) {
            setQuery(q);
            setCurrentPage(1);
            router.push(`/busqueda?${buildSearchParams(q, filters, 1)}`);
            performSearch(q, filters, 1);
        }
    };

    const handleFiltersChange = (newFilters: SearchFilterState) => {
        setFilters(newFilters);
        setCurrentPage(1);
        if (query.trim()) {
            router.push(`/busqueda?${buildSearchParams(query, newFilters, 1)}`);
            performSearch(query, newFilters, 1);
        }
    };

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        router.push(`/busqueda?${buildSearchParams(query, filters, page)}`);
        performSearch(query, filters, page);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Search Header */}
            <div className="border-b border-border bg-card">
                <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6 sm:py-8">
                    <h1 className="mb-4 sm:mb-6 font-display text-2xl sm:text-3xl font-bold text-foreground">
                        {t.pageTitle}
                    </h1>
                    {/* Search Bar */}
                    <div className="flex flex-col sm:flex-row gap-3 sm:gap-2">
                        <div className="relative flex-1">
                            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 sm:h-5 sm:w-5 -translate-y-1/2 text-muted-foreground z-10" />
                            <SearchAutocomplete
                                onSearch={(q) => {
                                    setQuery(q);
                                    handleSubmitQuery(q);
                                }}
                                placeholder={t.searchPlaceholder}
                                className="pl-10 bg-background text-sm sm:text-base"
                                defaultValue={initialQuery}
                            />
                        </div>
                        <Button disabled={loading} className="w-full sm:w-auto" onClick={() => handleSubmitQuery(query)}>
                            {loading ? (
                                <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
                            ) : (
                                t.searchButton
                            )}
                        </Button>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6 sm:py-8">
                {/* Mobile Filter Toggle */}
                <div className="lg:hidden mb-4">
                    <Button
                        variant="outline"
                        className="w-full flex items-center justify-center gap-2"
                        onClick={() => setShowFilters(!showFilters)}
                        aria-expanded={showFilters}
                        aria-controls="search-filters"
                    >
                        <FilterIcon className="h-4 w-4" />
                        {showFilters ? t.hideFilters : t.showFilters}
                        {!showFilters && total > 0 && (
                            <Badge variant="secondary" className="ml-auto">
                                {total} {t.results}
                            </Badge>
                        )}
                    </Button>
                </div>

                {/* Layout: Sidebar + Main */}
                <div className="flex flex-col lg:flex-row gap-6 sm:gap-8">
                    {/* Filters Sidebar */}
                    <aside id="search-filters" className={`lg:w-64 lg:flex-shrink-0 ${showFilters ? 'block' : 'hidden lg:block'}`}>
                        <SearchFilters
                            filters={filters}
                            onFiltersChange={handleFiltersChange}
                            resultCount={total}
                            facets={facets}
                        />
                    </aside>

                    {/* Results */}
                    <main className="flex-1 min-w-0">
                        {error && (
                            <div className="mb-6 rounded-lg bg-destructive/10 p-4 text-destructive">
                                {error}
                            </div>
                        )}

                        {loading && <SearchResultsSkeleton />}

                        {!loading && results.length === 0 && initialQuery && (
                            <div className="py-16 text-center">
                                <p className="text-lg text-muted-foreground">
                                    {t.noResultsFor} &quot;{initialQuery}&quot;
                                </p>
                                <p className="mt-2 text-sm text-muted-foreground">
                                    {t.tryDifferent}
                                </p>

                                {/* Suggest removing active filters */}
                                {(() => {
                                    const activeFilters: { label: string; reset: () => void }[] = [];
                                    if (filters.category && filters.category !== 'all')
                                        activeFilters.push({ label: filters.category, reset: () => handleFiltersChange({ ...filters, category: null }) });
                                    if (filters.state && filters.state !== 'all')
                                        activeFilters.push({ label: filters.state, reset: () => handleFiltersChange({ ...filters, state: null }) });
                                    if (filters.status !== 'all')
                                        activeFilters.push({ label: filters.status, reset: () => handleFiltersChange({ ...filters, status: 'all' }) });
                                    if (filters.law_type && filters.law_type !== 'all')
                                        activeFilters.push({ label: filters.law_type, reset: () => handleFiltersChange({ ...filters, law_type: 'all' }) });
                                    if (filters.jurisdiction.length !== 3)
                                        activeFilters.push({ label: 'jurisdiction', reset: () => handleFiltersChange({ ...filters, jurisdiction: ['federal', 'state', 'municipal'] }) });
                                    return activeFilters.length > 0 ? (
                                        <div className="mt-4">
                                            <p className="text-xs text-muted-foreground mb-2">{t.removeFilter}</p>
                                            <div className="flex flex-wrap justify-center gap-2">
                                                {activeFilters.map((f) => (
                                                    <button
                                                        key={f.label}
                                                        onClick={f.reset}
                                                        className="inline-flex items-center rounded-full border border-destructive/30 bg-destructive/5 px-3 py-1 text-sm text-destructive hover:bg-destructive/10 transition-colors"
                                                    >
                                                        &times; {f.label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    ) : null;
                                })()}

                                <div className="mt-6">
                                    <p className="text-xs text-muted-foreground mb-3">{t.suggestions}</p>
                                    <div className="flex flex-wrap justify-center gap-2">
                                        {['constitucion', 'codigo penal', 'trabajo', 'amparo'].map((term) => (
                                            <button
                                                key={term}
                                                onClick={() => handleSubmitQuery(term)}
                                                className="inline-flex items-center rounded-full border border-border px-3 py-1 text-sm text-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                                            >
                                                {term}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {!loading && results.length === 0 && !initialQuery && (
                            <div className="py-16 text-center">
                                <p className="text-lg text-muted-foreground">
                                    {t.enterSearchTerm}
                                </p>
                            </div>
                        )}

                        {!loading && results.length > 0 && (
                            <>
                                <div className="mb-4 sm:mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                                    <div className="flex items-center gap-3">
                                        <div className="text-xs sm:text-sm text-muted-foreground">
                                            {t.showing} {(currentPage - 1) * PAGE_SIZE + 1}-
                                            {Math.min(currentPage * PAGE_SIZE, total)} {t.of} {total} {total !== 1 ? t.resultPlural : t.result}
                                        </div>
                                        <button
                                            onClick={() => {
                                                navigator.clipboard.writeText(window.location.href);
                                                setShareCopied(true);
                                                setTimeout(() => setShareCopied(false), 2000);
                                            }}
                                            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                                            aria-label={t.shareSearch}
                                        >
                                            {shareCopied ? <Check className="h-3 w-3" /> : <Link2 className="h-3 w-3" />}
                                            <span className="hidden sm:inline">{shareCopied ? t.copied : t.shareSearch}</span>
                                        </button>
                                    </div>

                                    {totalPages > 1 && (
                                        <div className="text-xs sm:text-sm text-muted-foreground">
                                            {t.page} {currentPage} {t.pageOf} {totalPages}
                                        </div>
                                    )}
                                </div>

                                {/* Results List */}
                                <div className="space-y-4">
                                    {results.map((result, index) => (
                                        <Link
                                            href={`/leyes/${result.law_id}#article-${result.article.replace('Art. ', '')}`}
                                            key={result.id || index}
                                            className="block"
                                        >
                                            <Card className="transition-all hover:shadow-lg hover:border-primary/50 cursor-pointer">
                                                <CardContent className="p-4 sm:p-6">
                                                    <div className="flex items-start justify-between gap-4">
                                                        {/* Content */}
                                                        <div className="flex-1">
                                                            <div className="mb-2 flex flex-wrap items-center gap-1.5 sm:gap-2">
                                                                <Badge variant="secondary" className="font-mono text-xs truncate max-w-[200px] sm:max-w-[300px]">
                                                                    {result.law_name}
                                                                </Badge>
                                                                {result.tier && (
                                                                    <Badge variant="outline" className="text-xs capitalize">
                                                                        {result.tier}
                                                                    </Badge>
                                                                )}
                                                                {result.law_type === 'non_legislative' && (
                                                                    <Badge variant="secondary" className="text-xs bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                                                                        No Legislativa
                                                                    </Badge>
                                                                )}
                                                                {result.municipality && (
                                                                    <Badge variant="outline" className="text-xs">
                                                                        {result.municipality}
                                                                    </Badge>
                                                                )}
                                                                {result.article && (
                                                                    <span className="text-xs sm:text-sm text-muted-foreground font-medium">
                                                                        {result.article}
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {/* Hierarchy breadcrumb */}
                                                            {result.hierarchy && result.hierarchy.length > 0 && (
                                                                <div className="mb-1.5 text-xs text-muted-foreground truncate">
                                                                    {result.hierarchy.join(' \u203A ')}
                                                                </div>
                                                            )}

                                                            <div
                                                                className="text-sm text-foreground line-clamp-3"
                                                                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(result.snippet, { ALLOWED_TAGS: ['em', 'mark', 'b', 'strong'] }) }}
                                                            />

                                                            {result.date && (
                                                                <div className="mt-3 text-xs text-muted-foreground">
                                                                    {t.published} {new Date(result.date).toLocaleDateString(t.dateLocale, { year: 'numeric', month: 'long', day: 'numeric' })}
                                                                </div>
                                                            )}
                                                        </div>

                                                        {/* Score */}
                                                        {result.score && (
                                                            <div className="text-right hidden sm:block">
                                                                <div className="text-xs text-muted-foreground">{t.relevance}</div>
                                                                <div className="font-display text-lg font-bold text-primary-600">
                                                                    {result.score.toFixed(1)}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        </Link>
                                    ))}
                                </div>

                                {/* Pagination */}
                                {totalPages > 1 && (
                                    <Pagination
                                        currentPage={currentPage}
                                        totalPages={totalPages}
                                        onPageChange={handlePageChange}
                                        className="mt-8"
                                    />
                                )}
                            </>
                        )}
                    </main>
                </div>
            </div>
        </div>
    );
}

export default function SearchPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin" /></div>}>
            <SearchContent />
        </Suspense>
    );
}
