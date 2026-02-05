'use client';

import { useState, useEffect } from 'react';
import DOMPurify from 'isomorphic-dompurify';
import { Search as SearchIcon, Loader2, Filter as FilterIcon } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Input, Button, Card, CardContent, Badge } from "@leyesmx/ui";
import { SearchFilters, type SearchFilterState } from '@/components/SearchFilters';
import { Pagination } from '@/components/Pagination';
import { api } from '@/lib/api';
import type { SearchResult } from "@leyesmx/lib";

const DEFAULT_FILTERS: SearchFilterState = {
    jurisdiction: ['federal'],
    category: null,
    state: null,
    municipality: null,
    status: 'all',
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


    const [query, setQuery] = useState(initialQuery);
    const [filters, setFilters] = useState<SearchFilterState>({
        ...DEFAULT_FILTERS,
        jurisdiction: searchParams?.get('jurisdiction')?.split(',') || DEFAULT_FILTERS.jurisdiction,
        category: searchParams?.get('category') || DEFAULT_FILTERS.category,
        state: searchParams?.get('state') || DEFAULT_FILTERS.state,
        municipality: searchParams?.get('municipality') || DEFAULT_FILTERS.municipality,
        status: searchParams?.get('status') || DEFAULT_FILTERS.status,
        sort: searchParams?.get('sort') || DEFAULT_FILTERS.sort,
        date_range: searchParams?.get('date_range') || DEFAULT_FILTERS.date_range,
        title: searchParams?.get('title') || DEFAULT_FILTERS.title,
        chapter: searchParams?.get('chapter') || DEFAULT_FILTERS.chapter,
    });
    const [currentPage, setCurrentPage] = useState(1);
    const [results, setResults] = useState<SearchResult[]>([]);
    const [total, setTotal] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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

            if (data.warning) {
                setError(data.warning);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error al buscar');
            setResults([]);
            setTotal(0);
            setTotalPages(0);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim()) {
            // Update URL with query params
            const params = new URLSearchParams({ q: query });
            if (filters.jurisdiction.length) params.set('jurisdiction', filters.jurisdiction.join(','));
            if (filters.category) params.set('category', filters.category);
            if (filters.state) params.set('state', filters.state);
            if (filters.status !== 'all') params.set('status', filters.status);
            if (filters.sort !== 'relevance') params.set('sort', filters.sort);
            if (filters.date_range) params.set('date_range', filters.date_range);
            if (filters.title) params.set('title', filters.title);
            if (filters.chapter) params.set('chapter', filters.chapter);

            router.push(`/search?${params}`);

            // Reset to page 1 when new search
            setCurrentPage(1);
            performSearch(query, filters, 1);
        }
    };

    const handleFiltersChange = (newFilters: SearchFilterState) => {
        setFilters(newFilters);
        setCurrentPage(1); // Reset to page 1 when filters change
        if (query.trim()) {
            performSearch(query, newFilters, 1);
        }
    };

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        performSearch(query, filters, page);

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Search Header */}
            <div className="border-b border-border bg-card">
                <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6 sm:py-8">
                    <h1 className="mb-4 sm:mb-6 font-display text-2xl sm:text-3xl font-bold text-foreground">
                        Buscar Leyes
                    </h1>
                    {/* Search Bar */}
                    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 sm:gap-2">
                        <div className="relative flex-1">
                            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 sm:h-5 sm:w-5 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Buscar por artículo, título, contenido..."
                                className="pl-10 bg-background text-sm sm:text-base"
                            />
                        </div>
                        <Button type="submit" disabled={loading} className="w-full sm:w-auto">
                            {loading ? (
                                <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
                            ) : (
                                'Buscar'
                            )}
                        </Button>
                    </form>
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
                    >
                        <FilterIcon className="h-4 w-4" />
                        {showFilters ? 'Ocultar Filtros' : 'Mostrar Filtros'}
                        {!showFilters && total > 0 && (
                            <Badge variant="secondary" className="ml-auto">
                                {total} resultados
                            </Badge>
                        )}
                    </Button>
                </div>

                {/* Layout: Sidebar + Main */}
                <div className="flex flex-col lg:flex-row gap-6 sm:gap-8">
                    {/* Filters Sidebar */}
                    <aside className={`lg:w-64 lg:flex-shrink-0 ${showFilters ? 'block' : 'hidden lg:block'}`}>
                        <SearchFilters
                            filters={filters}
                            onFiltersChange={handleFiltersChange}
                            resultCount={total}
                        />
                    </aside>

                    {/* Results */}
                    <main className="flex-1 min-w-0">
                        {error && (
                            <div className="mb-6 rounded-lg bg-error-50 p-4 text-error-700 dark:bg-error-900 dark:text-error-100">
                                ⚠️ {error}
                            </div>
                        )}

                        {loading && (
                            <div className="flex items-center justify-center py-16">
                                <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
                            </div>
                        )}

                        {!loading && results.length === 0 && initialQuery && (
                            <div className="py-16 text-center">
                                <p className="text-lg text-muted-foreground">
                                    No se encontraron resultados para &quot;{initialQuery}&quot;
                                </p>
                                <p className="mt-2 text-sm text-muted-foreground">
                                    Intenta con otros términos de búsqueda o ajusta los filtros
                                </p>
                            </div>
                        )}

                        {!loading && results.length === 0 && !initialQuery && (
                            <div className="py-16 text-center">
                                <p className="text-lg text-muted-foreground">
                                    Ingresa un término de búsqueda para comenzar
                                </p>
                            </div>
                        )}

                        {!loading && results.length > 0 && (
                            <>
                                <div className="mb-4 sm:mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                                    <div className="text-xs sm:text-sm text-muted-foreground">
                                        Mostrando {(currentPage - 1) * PAGE_SIZE + 1}-
                                        {Math.min(currentPage * PAGE_SIZE, total)} de {total} resultado
                                        {total !== 1 ? 's' : ''}
                                    </div>

                                    {totalPages > 1 && (
                                        <div className="text-xs sm:text-sm text-muted-foreground">
                                            Página {currentPage} de {totalPages}
                                        </div>
                                    )}
                                </div>

                                {/* Results List */}
                                <div className="space-y-4">
                                    {results.map((result, index) => (
                                        <Link
                                            href={`/laws/${result.law_id}#article-${result.article.replace('Art. ', '')}`}
                                            key={result.id || index}
                                            className="block"
                                        >
                                            <Card className="transition-all hover:shadow-lg hover:border-primary/50 cursor-pointer">
                                                <CardContent className="p-4 sm:p-6">
                                                    <div className="flex items-start justify-between gap-4">
                                                        {/* Content */}
                                                        <div className="flex-1">
                                                            <div className="mb-2 flex flex-wrap items-center gap-1.5 sm:gap-2">
                                                                <Badge variant="secondary" className="font-mono text-[10px] sm:text-xs truncate max-w-[200px] sm:max-w-[300px]">
                                                                    {result.law_name}
                                                                </Badge>
                                                                {result.municipality && (
                                                                    <Badge variant="outline" className="text-[10px] sm:text-xs">
                                                                        📍 {result.municipality}
                                                                    </Badge>
                                                                )}
                                                                {result.article && (
                                                                    <span className="text-xs sm:text-sm text-muted-foreground font-medium">
                                                                        {result.article}
                                                                    </span>
                                                                )}
                                                            </div>

                                                            <div
                                                                className="text-sm text-foreground line-clamp-3"
                                                                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(result.snippet, { ALLOWED_TAGS: ['em', 'mark', 'b', 'strong'] }) }}
                                                            />

                                                            {result.date && (
                                                                <div className="mt-3 text-xs text-muted-foreground">
                                                                    Publicación: {new Date(result.date).toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' })}
                                                                </div>
                                                            )}
                                                        </div>

                                                        {/* Score */}
                                                        {result.score && (
                                                            <div className="text-right hidden sm:block">
                                                                <div className="text-xs text-muted-foreground">Relevancia</div>
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
