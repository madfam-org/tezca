'use client';
import { useState } from 'react';
import type { SearchResult } from '@leyesmx/lib';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from 'next/link';

export default function SearchExperience() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSearch = async () => {
        if (!query) return;
        setLoading(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
            const res = await fetch(`${apiUrl}/search/?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            setResults(data.results || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-4xl mx-auto p-4 space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Buscador de Leyes (Beta)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex gap-2">
                        <Input
                            placeholder="¿Qué dice la ley sobre...?"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        />
                        <Button onClick={handleSearch} disabled={loading}>
                            {loading ? 'Buscando...' : 'Buscar'}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <div className="space-y-4">
                {results.map((r) => (
                    <Link key={r.id} href={`/laws/${r.law_id}`} className="block">
                        <Card className="hover:bg-accent/50 transition-colors">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg font-bold text-primary">
                                    {r.law_id} - {r.article}
                                    {r.date && (
                                        <span className="ml-2 text-xs font-normal text-muted-foreground bg-secondary px-2 py-1 rounded">
                                            Vigente desde: {new Date(r.date + 'T12:00:00').toLocaleDateString('es-MX')}
                                        </span>
                                    )}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div
                                    className="text-sm text-muted-foreground prose dark:prose-invert max-w-none"
                                    dangerouslySetInnerHTML={{ __html: r.snippet }}
                                />
                            </CardContent>
                        </Card>
                    </Link>
                ))}
                {results.length === 0 && !loading && query && (
                    <div className="text-center text-muted-foreground">No se encontraron resultados.</div>
                )}
            </div>
        </div>
    );
}
