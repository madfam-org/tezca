'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Search, X, ArrowRight, FileText, Loader2 } from 'lucide-react';
import { Badge } from '@tezca/ui';
import { api } from '@/lib/api';
import { useLang, type Lang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        placeholder: 'Buscar leyes y artículos...',
        hint: 'Presiona',
        hintAction: 'para buscar',
        noResults: 'Sin resultados para',
        tryDifferent: 'Intenta con otros términos de búsqueda.',
        viewAll: 'Ver todos los resultados',
        close: 'Cerrar búsqueda',
        laws: 'Leyes',
    },
    en: {
        placeholder: 'Search laws and articles...',
        hint: 'Press',
        hintAction: 'to search',
        noResults: 'No results for',
        tryDifferent: 'Try different search terms.',
        viewAll: 'View all results',
        close: 'Close search',
        laws: 'Laws',
    },
    nah: {
        placeholder: 'Xictlatemo tenahuatilli...',
        hint: 'Xictequi',
        hintAction: 'ic tlatemoliztli',
        noResults: 'Ahmo oncah',
        tryDifferent: 'Xicyejyeco occē tlatemoliztli.',
        viewAll: 'Xiquitta mochi',
        close: 'Xictlatzacua tlatemoliztli',
        laws: 'Tenahuatilli',
    },
};

const TIER_LABELS: Record<Lang, Record<string, string>> = {
    es: { federal: 'Federal', state: 'Estatal', municipal: 'Municipal' },
    en: { federal: 'Federal', state: 'State', municipal: 'Municipal' },
    nah: { federal: 'Federal', state: 'Altepetl', municipal: 'Calpulli' },
};

interface Suggestion {
    id: string;
    name: string;
    tier: string;
}

export function CommandSearchTrigger() {
    const { lang } = useLang();
    const t = content[lang];
    const [open, setOpen] = useState(false);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setOpen(true);
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, []);

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                aria-label={t.placeholder}
            >
                <Search className="h-3.5 w-3.5" />
                <span className="hidden lg:inline">{t.placeholder}</span>
                <kbd className="hidden lg:inline-flex h-5 items-center gap-0.5 rounded border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                    <span className="text-xs">&#8984;</span>K
                </kbd>
            </button>
            {open && <CommandSearchDialog onClose={() => setOpen(false)} />}
        </>
    );
}

function CommandSearchDialog({ onClose }: { onClose: () => void }) {
    const { lang } = useLang();
    const t = content[lang];
    const tierLabels = TIER_LABELS[lang];
    const router = useRouter();
    const inputRef = useRef<HTMLInputElement>(null);
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [loading, setLoading] = useState(false);
    const [activeIndex, setActiveIndex] = useState(-1);
    const [searched, setSearched] = useState(false);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Focus input on mount
    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    // Close on Escape
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    // Lock body scroll
    useEffect(() => {
        document.body.style.overflow = 'hidden';
        return () => { document.body.style.overflow = ''; };
    }, []);

    const fetchSuggestions = useCallback(async (q: string) => {
        if (q.length < 2) {
            setSuggestions([]);
            setSearched(false);
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const results = await api.suggest(q);
            setSuggestions(results);
            setSearched(true);
            setActiveIndex(-1);
        } catch {
            setSuggestions([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => fetchSuggestions(query), 300);
        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
        };
    }, [query, fetchSuggestions]);

    const navigate = (path: string) => {
        onClose();
        router.push(path);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        const totalItems = suggestions.length + (query.trim() ? 1 : 0); // +1 for "view all"
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setActiveIndex(prev => (prev < totalItems - 1 ? prev + 1 : 0));
                break;
            case 'ArrowUp':
                e.preventDefault();
                setActiveIndex(prev => (prev > 0 ? prev - 1 : totalItems - 1));
                break;
            case 'Enter':
                e.preventDefault();
                if (activeIndex >= 0 && activeIndex < suggestions.length) {
                    navigate(`/leyes/${suggestions[activeIndex].id}`);
                } else if (query.trim()) {
                    navigate(`/busqueda?q=${encodeURIComponent(query)}`);
                }
                break;
        }
    };

    return (
        <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={t.placeholder}>
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-background/80 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Dialog */}
            <div className="relative mx-auto mt-[15vh] w-full max-w-lg px-4">
                <div className="overflow-hidden rounded-xl border border-border bg-popover shadow-2xl">
                    {/* Search input */}
                    <div className="flex items-center border-b border-border px-4">
                        <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <input
                            ref={inputRef}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={t.placeholder}
                            className="flex-1 bg-transparent px-3 py-3.5 text-sm text-foreground placeholder:text-muted-foreground outline-none"
                            role="combobox"
                            aria-expanded={suggestions.length > 0}
                            aria-controls="command-search-list"
                            aria-activedescendant={activeIndex >= 0 ? `cmd-item-${activeIndex}` : undefined}
                        />
                        {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                        <button
                            onClick={onClose}
                            className="ml-2 rounded p-1 text-muted-foreground hover:text-foreground transition-colors"
                            aria-label={t.close}
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </div>

                    {/* Results */}
                    <div id="command-search-list" role="listbox" className="max-h-80 overflow-y-auto">
                        {searched && suggestions.length === 0 && query.length >= 2 && !loading && (
                            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                                <p>{t.noResults} &ldquo;{query}&rdquo;</p>
                                <p className="mt-1 text-xs">{t.tryDifferent}</p>
                            </div>
                        )}

                        {suggestions.length > 0 && (
                            <div className="p-2">
                                <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                                    {t.laws}
                                </p>
                                {suggestions.map((item, index) => (
                                    <button
                                        key={item.id}
                                        id={`cmd-item-${index}`}
                                        role="option"
                                        aria-selected={index === activeIndex}
                                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                                            index === activeIndex
                                                ? 'bg-accent text-accent-foreground'
                                                : 'text-foreground hover:bg-muted'
                                        }`}
                                        onClick={() => navigate(`/leyes/${item.id}`)}
                                        onMouseEnter={() => setActiveIndex(index)}
                                    >
                                        <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                                        <span className="flex-1 truncate text-left">{item.name}</span>
                                        <Badge variant="secondary" className="text-xs flex-shrink-0">
                                            {tierLabels[item.tier] || item.tier}
                                        </Badge>
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* View all results action */}
                        {query.trim() && (
                            <div className="border-t border-border p-2">
                                <button
                                    id={`cmd-item-${suggestions.length}`}
                                    role="option"
                                    aria-selected={activeIndex === suggestions.length}
                                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                                        activeIndex === suggestions.length
                                            ? 'bg-accent text-accent-foreground'
                                            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                                    }`}
                                    onClick={() => navigate(`/busqueda?q=${encodeURIComponent(query)}`)}
                                    onMouseEnter={() => setActiveIndex(suggestions.length)}
                                >
                                    <Search className="h-4 w-4 flex-shrink-0" />
                                    <span className="flex-1 text-left">{t.viewAll} &ldquo;{query}&rdquo;</span>
                                    <ArrowRight className="h-4 w-4 flex-shrink-0" />
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Footer hint */}
                    <div className="border-t border-border px-4 py-2 flex items-center justify-between text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                            <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">&uarr;&darr;</kbd>
                            <span>{lang === 'es' ? 'navegar' : lang === 'en' ? 'navigate' : 'tlanemi'}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">&#9166;</kbd>
                            <span>{lang === 'es' ? 'seleccionar' : lang === 'en' ? 'select' : 'xictlapo'}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">esc</kbd>
                            <span>{lang === 'es' ? 'cerrar' : lang === 'en' ? 'close' : 'tlatzacua'}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
