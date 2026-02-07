'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, type SystemMetrics } from '@/lib/api';
import { Button, Card, CardHeader, CardTitle, CardContent } from "@tezca/ui";
import { ArrowLeft, BarChart3, Scale, Building2, Landmark, RefreshCw } from 'lucide-react';

function MetricCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: React.ComponentType<{ className?: string }> }) {
    return (
        <Card>
            <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-primary-100 dark:bg-primary-900 rounded-lg">
                        <Icon className="w-6 h-6 text-primary-600 dark:text-primary-300" />
                    </div>
                    <div>
                        <p className="text-sm text-muted-foreground">{label}</p>
                        <p className="text-2xl font-bold">{typeof value === 'number' ? value.toLocaleString() : value}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default function MetricsPage() {
    const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchMetrics = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await api.getMetrics();
            setMetrics(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error al cargar métricas');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchMetrics(); }, []);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button asChild variant="ghost" size="sm">
                        <Link href="/">
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Volver
                        </Link>
                    </Button>
                    <h1 className="text-3xl font-bold tracking-tight">Métricas del Sistema</h1>
                </div>
                <Button variant="outline" size="sm" onClick={fetchMetrics} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Actualizar
                </Button>
            </div>

            {error && (
                <div className="p-4 bg-error-50 text-error-700 rounded-lg border border-error-500/20">
                    {error}
                </div>
            )}

            {loading && !metrics ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => (
                        <Card key={i} className="animate-pulse">
                            <CardContent className="pt-6"><div className="h-16 bg-muted rounded" /></CardContent>
                        </Card>
                    ))}
                </div>
            ) : metrics && (
                <>
                    {/* Summary cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <MetricCard label="Total de Leyes" value={metrics.total_laws} icon={Scale} />
                        <MetricCard label="Federales" value={metrics.counts.federal} icon={Landmark} />
                        <MetricCard label="Estatales" value={metrics.counts.state} icon={Building2} />
                        <MetricCard label="Municipales" value={metrics.counts.municipal} icon={BarChart3} />
                    </div>

                    {/* Categories */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Categorías Principales</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {metrics.top_categories.length === 0 ? (
                                <p className="text-muted-foreground text-sm">Sin datos de categorías.</p>
                            ) : (
                                <div className="space-y-3">
                                    {metrics.top_categories.map((cat) => {
                                        const pct = metrics.total_laws > 0
                                            ? Math.round((cat.count / metrics.total_laws) * 100)
                                            : 0;
                                        return (
                                            <div key={cat.category} className="space-y-1">
                                                <div className="flex justify-between text-sm">
                                                    <span className="font-medium capitalize">{cat.category || 'Sin categoría'}</span>
                                                    <span className="text-muted-foreground">{cat.count.toLocaleString()} ({pct}%)</span>
                                                </div>
                                                <div className="h-2 bg-muted rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-primary-500 rounded-full transition-all"
                                                        style={{ width: `${pct}%` }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Quality distribution */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Distribución de Calidad</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {metrics.quality_distribution === null ? (
                                <p className="text-muted-foreground text-sm">
                                    La distribución de calidad por ley aún no está disponible en la base de datos.
                                    Se habilitará cuando se implemente el campo de grado por ley.
                                </p>
                            ) : (
                                <div className="grid grid-cols-5 gap-4 text-center">
                                    {Object.entries(metrics.quality_distribution).map(([grade, count]) => (
                                        <div key={grade} className="space-y-1">
                                            <div className="text-2xl font-bold">{grade}</div>
                                            <div className="text-sm text-muted-foreground">{count}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Last updated */}
                    <p className="text-xs text-muted-foreground text-right">
                        Última actualización: {new Date(metrics.last_updated).toLocaleString('es-MX')}
                    </p>
                </>
            )}
        </div>
    );
}
