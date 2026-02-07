'use client';

import { Search } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Button } from "@tezca/ui";
import { api } from '@/lib/api';
import { SearchAutocomplete } from '@/components/SearchAutocomplete';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        subtitle: 'El Espejo de la Ley',
        searchButton: 'Buscar',
        searchPlaceholder: 'Buscar leyes...',
        searchPlaceholderWithCount: (count: string) => `Buscar en ${count} leyes...`,
        tagline: 'Búsqueda inteligente en tiempo real • Actualizado diariamente',
    },
    en: {
        subtitle: 'The Mirror of the Law',
        searchButton: 'Search',
        searchPlaceholder: 'Search laws...',
        searchPlaceholderWithCount: (count: string) => `Search across ${count} laws...`,
        tagline: 'Real-time intelligent search • Updated daily',
    },
};

export function Hero() {
    const { lang } = useLang();
    const t = content[lang];
    const [totalLaws, setTotalLaws] = useState<number | null>(null);

    useEffect(() => {
        api.getStats()
            .then(stats => setTotalLaws(stats.total_laws))
            .catch(() => {});
    }, []);

    const handleSearch = (query: string) => {
        if (query.trim()) {
            window.location.href = `/search?q=${encodeURIComponent(query)}`;
        }
    };

    const locale = lang === 'es' ? 'es-MX' : 'en-US';
    const placeholder = totalLaws
        ? t.searchPlaceholderWithCount(totalLaws.toLocaleString(locale))
        : t.searchPlaceholder;

    return (
        <section className="relative overflow-hidden bg-gradient-to-br from-primary-500 via-primary-600 to-secondary-600 px-4 sm:px-6 py-16 sm:py-24 lg:py-32">
            {/* Animated background pattern */}
            <div className="absolute inset-0 bg-grid-pattern opacity-20" />

            <div className="relative mx-auto max-w-4xl text-center">
                {/* Icon */}
                <div className="mb-4 sm:mb-6 inline-flex animate-scale-in rounded-full bg-white/10 p-3 sm:p-4 backdrop-blur-sm">
                    <svg
                        aria-hidden="true"
                        className="h-10 w-10 sm:h-12 sm:w-12 lg:h-16 lg:w-16 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
                        />
                    </svg>
                </div>

                {/* Headline - Mobile-first responsive text sizing */}
                <h1 className="animate-slide-up font-display text-3xl sm:text-5xl lg:text-7xl font-bold tracking-tight text-white">
                    Tezca
                </h1>

                {/* Subheadline - Mobile-first responsive */}
                <p className="mt-3 sm:mt-4 animate-slide-up text-base sm:text-xl lg:text-2xl text-primary-100 [animation-delay:100ms]">
                    {t.subtitle}
                </p>

                {/* Search bar - Stacked on mobile, horizontal on larger screens */}
                <div className="mt-6 sm:mt-10 animate-slide-up [animation-delay:200ms]">
                    <div className="mx-auto max-w-2xl">
                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-2 rounded-xl bg-white dark:bg-neutral-900 p-3 sm:p-2 shadow-xl transition-all hover:shadow-2xl">
                            <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                                <Search className="h-5 w-5 sm:h-6 sm:w-6 text-neutral-400 dark:text-neutral-500 flex-shrink-0" />
                                <SearchAutocomplete
                                    onSearch={handleSearch}
                                    placeholder={placeholder}
                                    className="flex-1 border-0 bg-transparent text-base sm:text-lg text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus-visible:outline-none focus-visible:ring-0"
                                />
                            </div>
                            <Button
                                size="lg"
                                className="bg-primary-600 hover:bg-primary-700 w-full sm:w-auto"
                                onClick={() => handleSearch(document.querySelector<HTMLInputElement>('[role="combobox"]')?.value || '')}
                            >
                                {t.searchButton}
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Stats - Smaller text on mobile */}
                <div className="mt-6 sm:mt-8 text-xs sm:text-sm text-primary-100/80 animate-fade-in [animation-delay:300ms]">
                    {t.tagline}
                </div>
            </div>
        </section>
    );
}
