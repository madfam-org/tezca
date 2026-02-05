'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface Article {
    id: string;
    number: string;
    content: string;
    type: 'article' | 'transitorio';
}

interface LawData {
    law_id: string;
    articles: Article[];
    total_articles: number;
    total_transitorios: number;
}

interface LawArticlesProps {
    lawId: string;
}

export default function LawArticles({ lawId }: LawArticlesProps) {
    const [lawData, setLawData] = useState<LawData | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [showTransitorios, setShowTransitorios] = useState(false);

    useEffect(() => {
        async function loadLawData() {
            try {
                const response = await fetch(`/viewer_data/${lawId}.json`);
                if (!response.ok) throw new Error('Failed to load law data');
                const data = await response.json();
                setLawData(data);
            } catch (error) {
                console.error('Error loading law data:', error);
            } finally {
                setLoading(false);
            }
        }

        loadLawData();
    }, [lawId]);

    if (loading) {
        return (
            <Card className="p-8 text-center">
                <div className="animate-pulse">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mx-auto mb-4"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mx-auto"></div>
                </div>
                <p className="text-gray-600 dark:text-gray-400 mt-4">
                    Cargando artículos...
                </p>
            </Card>
        );
    }

    if (!lawData) {
        return (
            <Card className="p-8 text-center bg-red-50 dark:bg-red-950/30">
                <p className="text-red-600 dark:text-red-400">
                    Error al cargar los artículos. Por favor, intenta de nuevo.
                </p>
            </Card>
        );
    }

    const regularArticles = lawData.articles.filter(a => a.type === 'article');
    const transitorios = lawData.articles.filter(a => a.type === 'transitorio');

    const filteredArticles = (showTransitorios ? transitorios : regularArticles).filter(article => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
            article.number.toLowerCase().includes(query) ||
            article.content.toLowerCase().includes(query)
        );
    });

    return (
        <div>
            {/* Search and Filters */}
            <Card className="p-6 mb-6">
                <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1">
                        <Input
                            type="text"
                            placeholder="🔍 Buscar en artículos..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full"
                        />
                    </div>

                    {transitorios.length > 0 && (
                        <button
                            onClick={() => setShowTransitorios(!showTransitorios)}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${showTransitorios
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                                }`}
                        >
                            {showTransitorios ? 'Ver Artículos' : `Ver Transitorios (${transitorios.length})`}
                        </button>
                    )}
                </div>

                {searchQuery && (
                    <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
                        {filteredArticles.length} resultado{filteredArticles.length !== 1 ? 's' : ''} encontrado{filteredArticles.length !== 1 ? 's' : ''}
                    </div>
                )}
            </Card>

            {/* Articles List */}
            <div className="space-y-4">
                {filteredArticles.length === 0 ? (
                    <Card className="p-8 text-center glass border-dashed">
                        <p className="text-muted-foreground">
                            No se encontraron artículos que coincidan con tu búsqueda.
                        </p>
                    </Card>
                ) : (
                    filteredArticles.map((article, index) => (
                        <Card key={article.id} className="p-6 hover:shadow-lg transition-all duration-300 glass border-transparent hover:border-primary/20">
                            <div className="flex gap-4">
                                <div className="flex-shrink-0">
                                    <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center shadow-inner">
                                        <span className="text-primary-600 dark:text-primary-300 font-bold font-display text-sm">
                                            {index + 1}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex-1 min-w-0">
                                    <h3 className="text-lg font-bold font-display text-primary-700 dark:text-primary-300 mb-3">
                                        {article.number}
                                    </h3>

                                    {article.content ? (
                                        <div className="text-neutral-700 dark:text-neutral-300 leading-relaxed whitespace-pre-wrap font-serif">
                                            {searchQuery ? (
                                                <HighlightedText text={article.content} query={searchQuery} />
                                            ) : (
                                                article.content
                                            )}
                                        </div>
                                    ) : (
                                        <p className="text-muted-foreground italic">
                                            Contenido no disponible
                                        </p>
                                    )}
                                </div>
                            </div>
                        </Card>
                    ))
                )}
            </div>
        </div>
    );
}

function HighlightedText({ text, query }: { text: string; query: string }) {
    if (!query) return <>{text}</>;

    const parts = text.split(new RegExp(`(${query})`, 'gi'));

    return (
        <>
            {parts.map((part, i) => (
                part.toLowerCase() === query.toLowerCase() ? (
                    <mark key={i} className="bg-yellow-200 dark:bg-yellow-800">
                        {part}
                    </mark>
                ) : (
                    <span key={i}>{part}</span>
                )
            ))}
        </>
    );
}
