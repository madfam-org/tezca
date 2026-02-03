'use client';
import { useState } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SearchExperience() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSearch = async () => {
        if (!query) return;
        setLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/api/v1/search/?q=${encodeURIComponent(query)}`);
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
                {results.map((r: any) => (
                    <Card key={r.id} className="hover:bg-slate-50 transition-colors">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-lg font-bold text-blue-800">
                                {r.law} - {r.article}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div
                                className="text-sm text-gray-600 prose"
                                dangerouslySetInnerHTML={{ __html: r.snippet }}
                            />
                        </CardContent>
                    </Card>
                ))}
                {results.length === 0 && !loading && query && (
                    <div className="text-center text-gray-500">No se encontraron resultados.</div>
                )}
            </div>
        </div>
    );
}
