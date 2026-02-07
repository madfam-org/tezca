'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button, Card, CardContent } from "@tezca/ui";
import { ArrowLeft } from 'lucide-react';
import type { DashboardData } from '@/components/dataops/types';
import { CoverageHeader } from '@/components/dataops/CoverageHeader';
import { CoverageViewSelector } from '@/components/dataops/CoverageViewSelector';
import { TierProgressList } from '@/components/dataops/TierProgressList';
import { StateCoverageTable } from '@/components/dataops/StateCoverageTable';
import { GapSummaryPanel } from '@/components/dataops/GapSummaryPanel';
import { ExpansionPriorities } from '@/components/dataops/ExpansionPriorities';
import { HealthStatusGrid } from '@/components/dataops/HealthStatusGrid';

export default function DataOpsPage() {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeView, setActiveView] = useState('leyes_vigentes');

    const fetchDashboard = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await api.getCoverageDashboard();
            setData(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error al cargar el dashboard');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchDashboard(); }, []);

    return (
        <div className="space-y-6">
            {/* Nav */}
            <div className="flex items-center gap-4">
                <Button asChild variant="ghost" size="sm">
                    <Link href="/">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Volver
                    </Link>
                </Button>
            </div>

            {/* Header + refresh */}
            <CoverageHeader data={data} loading={loading} onRefresh={fetchDashboard} />

            {/* Error */}
            {error && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-lg border border-destructive/20">
                    <p>{error}</p>
                    <Button variant="outline" size="sm" className="mt-2" onClick={fetchDashboard}>
                        Reintentar
                    </Button>
                </div>
            )}

            {/* Loading skeleton */}
            {loading && !data ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[1, 2, 3, 4].map(i => (
                        <Card key={i} className="animate-pulse">
                            <CardContent className="pt-6"><div className="h-32 bg-muted rounded" /></CardContent>
                        </Card>
                    ))}
                </div>
            ) : data && (
                <>
                    {/* Coverage view selector */}
                    {data.coverage_views && (
                        <CoverageViewSelector
                            views={data.coverage_views}
                            activeView={activeView}
                            onSelect={setActiveView}
                        />
                    )}

                    {/* Active view summary card */}
                    {data.coverage_views[activeView] && (
                        <Card>
                            <CardContent className="pt-6">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-sm text-muted-foreground">
                                            {data.coverage_views[activeView].label}
                                        </p>
                                        <p className="text-4xl font-bold tabular-nums">
                                            {data.coverage_views[activeView].captured.toLocaleString()}
                                            <span className="text-lg text-muted-foreground font-normal">
                                                {' '}/ {data.coverage_views[activeView].universe.toLocaleString()}
                                            </span>
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-4xl font-bold tabular-nums">
                                            {data.coverage_views[activeView].pct}%
                                        </p>
                                        <p className="text-xs text-muted-foreground">cobertura</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Tier progress */}
                    <TierProgressList tiers={data.tier_progress} />

                    {/* State coverage table */}
                    <StateCoverageTable states={data.state_coverage} />

                    {/* Two-column grid: gaps + priorities */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <GapSummaryPanel gaps={data.gap_summary} />
                        <ExpansionPriorities priorities={data.expansion_priorities} />
                    </div>

                    {/* Health status */}
                    <HealthStatusGrid health={data.health_status} />
                </>
            )}
        </div>
    );
}
