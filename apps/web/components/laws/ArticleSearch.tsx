'use client';

import { useState, useRef, useCallback } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import DOMPurify from 'dompurify';
import { api } from '@/lib/api';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        placeholder: 'Buscar dentro de esta ley...',
        results: 'resultados',
        result: 'resultado',
        noResults: 'Sin resultados',
        clear: 'Limpiar busqueda',
    },
    en: {
        placeholder: 'Search within this law...',
        results: 'results',
        result: 'result',
        noResults: 'No results',
        clear: 'Clear search',
    },
    nah: {
        placeholder: 'Xictlatemo inīn tenahuatilli...',
        results: 'tlanextīliztli',
        result: 'tlanextīliztli',
        noResults: 'Ahmo tlanextīliztli',
        clear: 'Xicchīpahua tlatemoliztli',
    },
};

interface ArticleSearchResult {
    article_id: string;
    snippet: string;
    score: number;
}

interface ArticleSearchProps {
    lawId: string;
    onResultClick: (articleId: string) => void;
}

export function ArticleSearch({ lawId, onResultClick }: ArticleSearchProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<ArticleSearchResult[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [showResults, setShowResults] = useState(false);
    const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

    const doSearch = useCallback(async (q: string) => {
        if (!q.trim()) {
            setResults([]);
            setTotal(0);
            setShowResults(false);
            return;
        }
        setLoading(true);
        try {
            const data = await api.searchWithinLaw(lawId, q);
            setResults(data.results || []);
            setTotal(data.total || 0);
            setShowResults(true);
        } catch {
            setResults([]);
            setTotal(0);
        } finally {
            setLoading(false);
        }
    }, [lawId]);

    const handleChange = (value: string) => {
        setQuery(value);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => doSearch(value), 300);
    };

    const handleClear = () => {
        setQuery('');
        setResults([]);
        setTotal(0);
        setShowResults(false);
    };

    const handleResultClick = (articleId: string) => {
        onResultClick(articleId);
        setShowResults(false);
    };

    return (
        <div className="relative">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                    type="text"
                    value={query}
                    onChange={(e) => handleChange(e.target.value)}
                    placeholder={t.placeholder}
                    className="w-full rounded-lg border border-input bg-background pl-10 pr-10 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    aria-label={t.placeholder}
                />
                {loading && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                )}
                {!loading && query && (
                    <button
                        onClick={handleClear}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        aria-label={t.clear}
                    >
                        <X className="h-4 w-4" />
                    </button>
                )}
            </div>

            {showResults && (
                <div className="absolute z-20 mt-1 w-full rounded-lg border bg-popover shadow-lg max-h-80 overflow-y-auto">
                    {results.length === 0 ? (
                        <div className="p-3 text-sm text-muted-foreground text-center">
                            {t.noResults}
                        </div>
                    ) : (
                        <>
                            <div className="px-3 py-2 text-xs text-muted-foreground border-b">
                                {total} {total === 1 ? t.result : t.results}
                            </div>
                            {results.map((r) => (
                                <button
                                    key={r.article_id}
                                    onClick={() => handleResultClick(r.article_id)}
                                    className="w-full text-left px-3 py-2 hover:bg-accent transition-colors border-b last:border-b-0"
                                >
                                    <div className="text-xs font-semibold text-primary mb-0.5">
                                        Art. {r.article_id}
                                    </div>
                                    <div
                                        className="text-xs text-muted-foreground line-clamp-2"
                                        dangerouslySetInnerHTML={{
                                            __html: DOMPurify.sanitize(r.snippet, {
                                                ALLOWED_TAGS: ['em', 'mark', 'b', 'strong'],
                                            }),
                                        }}
                                    />
                                </button>
                            ))}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
