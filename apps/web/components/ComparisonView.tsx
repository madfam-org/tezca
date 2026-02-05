'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { LawArticleResponse } from "@leyesmx/lib";
import { Card, Badge, Button } from "@leyesmx/ui";
import Link from 'next/link';
import { ArrowLeft, Loader2 } from 'lucide-react';

interface ComparisonViewProps {
    lawIds: string[];
}

export default function ComparisonView({ lawIds }: ComparisonViewProps) {
    const [laws, setLaws] = useState<LawArticleResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchLaws() {
            if (lawIds.length === 0) {
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                // Fetch all laws in parallel
                const responses = await Promise.all(
                    lawIds.map(id => api.getLawArticles(id))
                );
                setLaws(responses);
            } catch (err) {
                console.error("Failed to fetch laws for comparison", err);
                setError("Error loading laws. Please try again.");
            } finally {
                setLoading(false);
            }
        }

        fetchLaws();
    }, [lawIds]);

    if (loading) {
        return (
            <div className="flex h-[80vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-2">Cargando leyes para comparación...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
                <h3 className="text-xl font-bold text-destructive mb-2">Error</h3>
                <p className="text-muted-foreground mb-4">{error}</p>
                <Button asChild variant="outline">
                    <Link href="/">Volver al inicio</Link>
                </Button>
            </div>
        );
    }

    if (laws.length === 0) {
        return (
            <div className="text-center py-20">
                <h2 className="text-2xl font-bold mb-4">No hay leyes seleccionadas</h2>
                <Button asChild>
                    <Link href="/">Seleccionar Leyes</Link>
                </Button>
            </div>
        );
    }

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col">
            <div className="mb-4 flex items-center gap-4">
                <Button asChild variant="ghost" size="sm">
                    <Link href="/">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Atrás
                    </Link>
                </Button>
                <h1 className="text-2xl font-bold">Comparación de Leyes</h1>
            </div>

            <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 h-full overflow-hidden">
                {laws.map((law, index) => (
                    <Card key={law.law_id} className="flex flex-col h-full overflow-hidden border border-white/20 shadow-xl glass">
                        <div className="p-4 border-b border-white/10 bg-white/5 backdrop-blur-md">
                            <h2 className="font-display font-bold text-lg leading-tight mb-2 line-clamp-2 text-primary-700 dark:text-primary-300" title={law.law_name}>
                                {law.law_name}
                            </h2>
                            <div className="flex gap-2 flex-wrap">
                                <Badge variant="outline" className="bg-background/50 backdrop-blur border-primary/20">{law.articles.length} artículos</Badge>
                                <Badge variant="secondary" className="bg-secondary-100 dark:bg-secondary-900/50 text-secondary-700 dark:text-secondary-300">{law.law_id}</Badge>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 bg-white/40 dark:bg-black/20 backdrop-blur-sm scroll-smooth">
                            <div className="prose dark:prose-invert max-w-none text-sm">
                                {law.articles.map((article) => (
                                    <div key={article.article_id} className="mb-6 p-5 rounded-xl hover:bg-white/40 dark:hover:bg-white/5 transition-all duration-300 border border-transparent hover:border-primary/10 shadow-sm hover:shadow-md group">
                                        <h3 className="font-display font-bold text-primary-600 dark:text-primary-400 mb-2 sticky top-0 bg-white/90 dark:bg-neutral-900/90 backdrop-blur-md py-1.5 border-b border-primary/10 w-fit z-10 px-3 rounded-lg shadow-sm">
                                            {article.article_id}
                                        </h3>
                                        <div className="leading-relaxed whitespace-pre-wrap font-serif text-neutral-700 dark:text-neutral-300 group-hover:text-neutral-900 dark:group-hover:text-neutral-100 transition-colors">
                                            {article.text}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
}
