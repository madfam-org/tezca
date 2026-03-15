'use client';

import { useState, useRef, useMemo, useCallback } from 'react';
import { Search, X } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';
import { trackEvent } from '@/lib/analytics/posthog';

const content = {
    es: { placeholder: 'Buscar ley...', clear: 'Limpiar búsqueda' },
    en: { placeholder: 'Search law...', clear: 'Clear search' },
    nah: { placeholder: 'Xictēmoa tenahuatilli...', clear: 'Xictlachīhua' },
};

interface SearchNode {
    id: string;
    label: string;
}

interface GraphSearchProps {
    nodes: SearchNode[];
    onFocus: (nodeId: string) => void;
    onClear: () => void;
}

export function GraphSearch({ nodes, onFocus, onClear }: GraphSearchProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [query, setQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);

    const filtered = useMemo(() =>
        query.length >= 2
            ? nodes.filter((n) => n.label.toLowerCase().includes(query.toLowerCase())).slice(0, 8)
            : [],
    [query, nodes]);

    const handleSelect = useCallback((nodeId: string) => {
        onFocus(nodeId);
        setIsOpen(false);
        trackEvent('graph.node_searched', { node_id: nodeId, query });
        setQuery('');
    }, [onFocus, query]);

    const handleClear = useCallback(() => {
        setQuery('');
        setIsOpen(false);
        onClear();
    }, [onClear]);

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
            handleClear();
            inputRef.current?.blur();
            return;
        }
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIndex((i) => Math.max(i - 1, 0));
        }
        if (e.key === 'Enter' && filtered[selectedIndex]) {
            handleSelect(filtered[selectedIndex].id);
        }
    }, [filtered, selectedIndex, handleSelect, handleClear]);

    return (
        <div className="absolute top-3 right-3 z-10 w-64 max-w-[calc(100vw-2rem)]">
            <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); setIsOpen(true); }}
                    onFocus={() => setIsOpen(true)}
                    onKeyDown={handleKeyDown}
                    placeholder={t.placeholder}
                    className="w-full rounded-lg border bg-card/90 backdrop-blur-sm pl-8 pr-8 py-2 text-sm shadow-md focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                {query && (
                    <button
                        onClick={handleClear}
                        className="absolute right-2.5 top-2.5"
                        aria-label={t.clear}
                    >
                        <X className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                    </button>
                )}
            </div>

            {isOpen && filtered.length > 0 && (
                <ul className="mt-1 max-h-56 overflow-auto rounded-lg border bg-card/95 backdrop-blur-sm shadow-md text-sm">
                    {filtered.map((node, i) => (
                        <li key={node.id}>
                            <button
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={() => handleSelect(node.id)}
                                className={`w-full text-left px-3 py-2 truncate transition-colors ${
                                    i === selectedIndex
                                        ? 'bg-primary/10 text-primary'
                                        : 'hover:bg-muted'
                                }`}
                            >
                                {node.label}
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
