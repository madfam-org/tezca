'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@tezca/ui';
import { Badge } from '@tezca/ui';
import { api } from '@/lib/api';
import { useLang } from '@/components/providers/LanguageContext';
import type { Lang } from '@/components/providers/LanguageContext';

interface Suggestion {
    id: string;
    name: string;
    tier: string;
}

interface SearchAutocompleteProps {
    onSearch: (query: string) => void;
    placeholder?: string;
    className?: string;
    defaultValue?: string;
}

const TIER_LABELS: Record<Lang, Record<string, string>> = {
    es: { federal: 'Federal', state: 'Estatal', municipal: 'Municipal' },
    en: { federal: 'Federal', state: 'State', municipal: 'Municipal' },
};

export function SearchAutocomplete({ onSearch, placeholder, className, defaultValue = '' }: SearchAutocompleteProps) {
    const { lang } = useLang();
    const tierLabels = TIER_LABELS[lang];
    const router = useRouter();
    const [query, setQuery] = useState(defaultValue);
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [activeIndex, setActiveIndex] = useState(-1);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const listboxId = 'search-autocomplete-listbox';

    const fetchSuggestions = useCallback(async (q: string) => {
        if (q.length < 2) {
            setSuggestions([]);
            setIsOpen(false);
            return;
        }
        try {
            const results = await api.suggest(q);
            setSuggestions(results);
            setIsOpen(results.length > 0);
            setActiveIndex(-1);
        } catch {
            setSuggestions([]);
            setIsOpen(false);
        }
    }, []);

    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => fetchSuggestions(query), 300);
        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
        };
    }, [query, fetchSuggestions]);

    // Close on outside click
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!isOpen) {
            if (e.key === 'Enter') {
                e.preventDefault();
                onSearch(query);
            }
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setActiveIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : 0));
                break;
            case 'ArrowUp':
                e.preventDefault();
                setActiveIndex(prev => (prev > 0 ? prev - 1 : suggestions.length - 1));
                break;
            case 'Enter':
                e.preventDefault();
                if (activeIndex >= 0 && activeIndex < suggestions.length) {
                    router.push(`/laws/${suggestions[activeIndex].id}`);
                    setIsOpen(false);
                } else {
                    setIsOpen(false);
                    onSearch(query);
                }
                break;
            case 'Escape':
                setIsOpen(false);
                setActiveIndex(-1);
                break;
        }
    };

    const handleSuggestionClick = (suggestion: Suggestion) => {
        setIsOpen(false);
        router.push(`/laws/${suggestion.id}`);
    };

    return (
        <div ref={containerRef} className="relative">
            <Input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => { if (suggestions.length > 0) setIsOpen(true); }}
                placeholder={placeholder}
                className={className}
                role="combobox"
                aria-expanded={isOpen}
                aria-controls={listboxId}
                aria-activedescendant={activeIndex >= 0 ? `suggestion-${activeIndex}` : undefined}
                aria-autocomplete="list"
            />
            {isOpen && suggestions.length > 0 && (
                <ul
                    id={listboxId}
                    role="listbox"
                    className="absolute z-50 mt-1 w-full rounded-lg border border-border bg-popover shadow-lg backdrop-blur-sm max-h-80 overflow-y-auto"
                >
                    {suggestions.map((suggestion, index) => (
                        <li
                            key={suggestion.id}
                            id={`suggestion-${index}`}
                            role="option"
                            aria-selected={index === activeIndex}
                            className={`flex items-center justify-between gap-2 px-3 py-2.5 cursor-pointer text-sm transition-colors ${
                                index === activeIndex ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'
                            }`}
                            onMouseDown={(e) => { e.preventDefault(); handleSuggestionClick(suggestion); }}
                            onMouseEnter={() => setActiveIndex(index)}
                        >
                            <span className="truncate text-foreground">{suggestion.name}</span>
                            <Badge variant="secondary" className="text-[10px] flex-shrink-0">
                                {tierLabels[suggestion.tier] || suggestion.tier}
                            </Badge>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
