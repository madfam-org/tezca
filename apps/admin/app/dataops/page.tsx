'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button, Card, CardHeader, CardTitle, CardContent, Badge } from "@leyesmx/ui";
import { ArrowLeft, RefreshCw, Database, Activity, AlertTriangle } from 'lucide-react';

interface CoverageData {
    summary: { total_in_db: number; total_scraped: number; total_gaps: number; actionable_gaps: number };
    federal: { laws_in_db: number; laws_scraped: number };
    state: { total_in_db: number; total_scraped: number; total_permanent_gaps: number };
    municipal: { total_in_db: number; total_scraped: number; cities_covered: number };
    gaps: { total: number; open: number; in_progress: number; resolved: number; permanent: number };
}

interface HealthData {
    total_sources: number;
    healthy: number;
    degraded: number;
    down: number;
    unknown: number;
    never_checked: number;
}

interface GapData {
    total: number;
    by_status: Record<string, number>;
    by_tier: Record<string, number>;
    by_level: Record<string, number>;
    actionable: number;
    overdue: number;
}

export default function DataOpsPage() {
    const [coverage, setCoverage] = useState<CoverageData | null>(null);
    const [health, setHealth] = useState<HealthData | null>(null);
    const [gaps, setGaps] = useState<GapData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchAll = async () => {
        setLoading(true);
        setError(null);
        try {
            const [covData, healthData, gapData] = await Promise.all([
                api.getCoverage(),
                api.getHealthSources(),
                api.getGaps(),
            ]);
            setCoverage(covData as unknown as CoverageData);
            setHealth(healthData as unknown as HealthData);
            setGaps(gapData as unknown as GapData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error al cargar datos de DataOps');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAll(); }, []);

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
                    <h1 className="text-3xl font-bold tracking-tight">DataOps</h1>
                </div>
                <Button variant="outline" size="sm" onClick={fetchAll} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Actualizar
                </Button>
            </div>

            {error && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-lg border border-destructive/20">
                    <p>{error}</p>
                    <Button variant="outline" size="sm" className="mt-2" onClick={fetchAll}>
                        Reintentar
                    </Button>
                </div>
            )}

            {loading && !coverage ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[1, 2, 3].map(i => (
                        <Card key={i} className="animate-pulse">
                            <CardContent className="pt-6"><div className="h-24 bg-muted rounded" /></CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <>
                    {/* Coverage Cards */}
                    {coverage && (
                        <div>
                            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                                <Database className="w-5 h-5" />
                                Cobertura de Datos
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <Card>
                                    <CardContent className="pt-6 text-center">
                                        <p className="text-sm text-muted-foreground">Federal</p>
                                        <p className="text-3xl font-bold">{coverage.federal.laws_in_db.toLocaleString()}</p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {coverage.federal.laws_scraped.toLocaleString()} scrapeadas
                                        </p>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardContent className="pt-6 text-center">
                                        <p className="text-sm text-muted-foreground">Estatal</p>
                                        <p className="text-3xl font-bold">{coverage.state.total_in_db.toLocaleString()}</p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {coverage.state.total_permanent_gaps} brechas permanentes
                                        </p>
                                    </CardContent>
                                </Card>
                                <Card>
                                    <CardContent className="pt-6 text-center">
                                        <p className="text-sm text-muted-foreground">Municipal</p>
                                        <p className="text-3xl font-bold">{coverage.municipal.total_in_db.toLocaleString()}</p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            {coverage.municipal.cities_covered} ciudades cubiertas
                                        </p>
                                    </CardContent>
                                </Card>
                            </div>
                        </div>
                    )}

                    {/* Source Health */}
                    {health && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <Activity className="w-5 h-5" />
                                    Salud de Fuentes
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-center">
                                    <div>
                                        <p className="text-2xl font-bold">{health.total_sources}</p>
                                        <p className="text-xs text-muted-foreground">Total</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-green-600">{health.healthy}</p>
                                        <p className="text-xs text-muted-foreground">Saludables</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-yellow-600">{health.degraded}</p>
                                        <p className="text-xs text-muted-foreground">Degradadas</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-red-600">{health.down}</p>
                                        <p className="text-xs text-muted-foreground">Caídas</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-gray-500">{health.unknown}</p>
                                        <p className="text-xs text-muted-foreground">Desconocido</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-gray-400">{health.never_checked}</p>
                                        <p className="text-xs text-muted-foreground">Sin verificar</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Gap Summary */}
                    {gaps && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <AlertTriangle className="w-5 h-5" />
                                    Brechas de Datos
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                                    <div>
                                        <p className="text-2xl font-bold">{gaps.total}</p>
                                        <p className="text-xs text-muted-foreground">Total</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-green-600">
                                            {gaps.by_status?.resolved ?? 0}
                                        </p>
                                        <p className="text-xs text-muted-foreground">Resueltas</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-orange-600">{gaps.actionable}</p>
                                        <p className="text-xs text-muted-foreground">Accionables</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-red-600">{gaps.overdue}</p>
                                        <p className="text-xs text-muted-foreground">Vencidas</p>
                                    </div>
                                </div>

                                {Object.keys(gaps.by_status).length > 0 && (
                                    <div>
                                        <p className="text-sm font-medium mb-2">Por estado</p>
                                        <div className="flex flex-wrap gap-2">
                                            {Object.entries(gaps.by_status).map(([status, count]) => (
                                                <Badge key={status} variant="secondary">
                                                    {status}: {count}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}
                </>
            )}
        </div>
    );
}
