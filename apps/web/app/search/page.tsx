'use client';

import { useState, useEffect } from 'react';
import { Search as SearchIcon, Loader2 } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SearchFilters, type SearchFilterState } from '@/components/SearchFilters';
import { Pagination } from '@/components/Pagination';
import { api } from '@/lib/api';
import type { SearchResult } from '@/lib/types';

const DEFAULT_FILTERS: SearchFilterState = {
    jurisdiction: ['federal'],
    category: null,
    state: null,
    status: 'all',
    sort: 'relevance',
};

const PAGE_SIZE = 10;

import { Suspense } from 'react';

function SearchContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const initialQuery = searchParams?.get('q') || '';

    const [query, setQuery] = useState(initialQuery);
    const [filters, setFilters] = useState<SearchFilterState>(DEFAULT_FILTERS);
    const [currentPage, setCurrentPage] = useState(1);
    const [results, setResults] = useState<SearchResult[]>([]);
    const [total, setTotal] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Perform search when query or filters change
    useEffect(() => {
        if (initialQuery) {
            performSearch(initialQuery, filters, currentPage);
        }
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
                status: searchFilters.status,
                sort: searchFilters.sort,
                date_range: searchFilters.date_range,
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
                <div className="mx-auto max-w-6xl px-6 py-8">
                    <h1 className="mb-6 font-display text-3xl font-bold text-foreground">
                        Buscar Leyes
                    </h1>

                    <form onSubmit={handleSubmit}>
                        <div className="relative flex items-center gap-2 rounded-lg bg-background p-2 shadow-md ring-1 ring-border">
                            <SearchIcon className="ml-2 h-5 w-5 text-muted-foreground" />
                            <Input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Buscar en 330 leyes federales..."
                                className="flex-1 border-0 bg-transparent text-base focus-visible:outline-none focus-visible:ring-0"
                                autoFocus
                            />
                            <Button type="submit" disabled={loading}>
                                {loading ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Buscando...
                                    </>
                                ) : (
                                    'Buscar'
                                )}
                            </Button>
                        </div>
                    </form>
                </div>
            </div>

            {/* Main Content */}
            <div className="mx-auto max-w-6xl px-6 py-8">
                <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
                    {/* Filters Sidebar */}
                    <aside>
                        <SearchFilters
                            filters={filters}
                            onFiltersChange={handleFiltersChange}
                            resultCount={total}
                        />
                    </aside>

                    {/* Results */}
                    <main>
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
                                <div className="mb-6 flex items-center justify-between">
                                    <div className="text-sm text-muted-foreground">
                                        Mostrando {(currentPage - 1) * PAGE_SIZE + 1}-
                                        {Math.min(currentPage * PAGE_SIZE, total)} de {total} resultado
                                        {total !== 1 ? 's' : ''}
                                    </div>

                                    {totalPages > 1 && (
                                        <div className="text-sm text-muted-foreground">
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
                                                <CardContent className="p-6">
                                                    <div className="flex items-start justify-between gap-4">
                                                        {/* Content */}
                                                        <div className="flex-1">
                                                            <div className="mb-2 flex flex-wrap items-center gap-2">
                                                                <Badge variant="secondary" className="font-mono text-xs truncate max-w-[300px]">
                                                                    {result.law_name}
                                                                </Badge>
                                                                {result.article && (
                                                                    <span className="text-sm text-muted-foreground font-medium">
                                                                        {result.article}
                                                                    </span>
                                                                )}
                                                            </div>

                                                            <div
                                                                className="text-sm text-foreground line-clamp-3"
                                                                dangerouslySetInnerHTML={{ __html: result.snippet }}
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
