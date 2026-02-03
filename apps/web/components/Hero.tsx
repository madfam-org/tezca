'use client';

import { Search } from 'lucide-react';
import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export function Hero() {
    const [searchQuery, setSearchQuery] = useState('');

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchQuery.trim()) {
            window.location.href = `/search?q=${encodeURIComponent(searchQuery)}`;
        }
    };

    return (
        <section className="relative overflow-hidden bg-gradient-to-br from-primary-500 via-primary-600 to-secondary-600 px-6 py-24 sm:py-32">
            {/* Animated background pattern */}
            <div className="absolute inset-0 bg-grid-pattern opacity-20" />

            <div className="relative mx-auto max-w-4xl text-center">
                {/* Icon */}
                <div className="mb-6 inline-flex animate-scale-in rounded-full bg-white/10 p-4 backdrop-blur-sm">
                    <svg
                        className="h-12 w-12 text-white sm:h-16 sm:w-16"
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

                {/* Headline */}
                <h1 className="animate-slide-up font-display text-5xl font-bold tracking-tight text-white sm:text-7xl">
                    Leyes Como Código
                </h1>

                {/* Subheadline */}
                <p className="mt-4 animate-slide-up text-xl text-primary-100 sm:text-2xl [animation-delay:100ms]">
                    El Sistema Legal Mexicano, Digitalizado
                </p>

                {/* Search bar */}
                <div className="mt-10 animate-slide-up [animation-delay:200ms]">
                    <form onSubmit={handleSearch} className="mx-auto max-w-2xl">
                        <div className="relative flex items-center gap-2 rounded-xl bg-white p-2 shadow-xl transition-all hover:shadow-2xl">
                            <Search className="ml-3 h-6 w-6 text-neutral-400" />
                            <Input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Buscar en 11,667 leyes..."
                                className="flex-1 border-0 bg-transparent text-lg text-neutral-900 placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-0"
                            />
                            <Button
                                type="submit"
                                size="lg"
                                className="bg-primary-600 hover:bg-primary-700"
                            >
                                Buscar
                            </Button>
                        </div>
                    </form>
                </div>

                {/* Stats */}
                <div className="mt-8 text-sm text-primary-100/80 animate-fade-in [animation-delay:300ms]">
                    Búsqueda inteligente en tiempo real • Actualizado diariamente
                </div>
            </div>
        </section>
    );
}

function Stat({ value, label }: { value: string; label: string }) {
    return (
        <div className="flex flex-col items-center gap-1">
            <div className="text-3xl font-bold text-white sm:text-4xl">{value}</div>
            <div className="text-sm uppercase tracking-wider">{label}</div>
        </div>
    );
}
