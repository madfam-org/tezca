'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button, Card, CardHeader, CardTitle, CardContent, Badge } from "@tezca/ui";
import { ArrowLeft, RefreshCw, Rocket, ChevronDown, ChevronRight } from 'lucide-react';
import type { RoadmapData, RoadmapPhase, RoadmapItemData } from '@/components/dataops/types';

const STATUS_OPTIONS = ['planned', 'in_progress', 'blocked', 'completed', 'deferred'] as const;

const STATUS_STYLES: Record<string, string> = {
    planned: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
    in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    blocked: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    deferred: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
};

const CATEGORY_STYLES: Record<string, string> = {
    fix: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    scraper: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    outreach: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
    investigation: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    partnership: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
    infrastructure: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
};

function PhaseProgressBar({ phase }: { phase: RoadmapPhase }) {
    const pct = phase.total > 0 ? Math.round((phase.completed / phase.total) * 100) : 0;
    return (
        <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="h-2 flex-1 bg-muted rounded-full overflow-hidden">
                <div
                    className="h-full bg-green-500 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                />
            </div>
            <span className="text-xs text-muted-foreground shrink-0 tabular-nums w-10 text-right">
                {phase.completed}/{phase.total}
            </span>
        </div>
    );
}

function RoadmapItemRow({
    item,
    onStatusChange,
    updating,
}: {
    item: RoadmapItemData;
    onStatusChange: (id: number, status: string) => void;
    updating: number | null;
}) {
    return (
        <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/40 transition-colors border border-transparent hover:border-muted">
            <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium">{item.title}</p>
                    <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${CATEGORY_STYLES[item.category] ?? ''}`}>
                        {item.category}
                    </Badge>
                </div>
                {item.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2">{item.description}</p>
                )}
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    {item.estimated_laws > 0 && (
                        <span>+{item.estimated_laws.toLocaleString()} leyes</span>
                    )}
                    {item.estimated_effort && (
                        <span>Esfuerzo: {item.estimated_effort}</span>
                    )}
                    {item.progress_pct > 0 && item.status !== 'completed' && (
                        <span>{item.progress_pct}%</span>
                    )}
                </div>
                {item.notes && (
                    <p className="text-xs italic text-muted-foreground">{item.notes}</p>
                )}
            </div>
            <div className="shrink-0">
                <select
                    value={item.status}
                    onChange={(e) => onStatusChange(item.id, e.target.value)}
                    disabled={updating === item.id}
                    className={`text-xs rounded-md px-2 py-1 border border-muted cursor-pointer ${STATUS_STYLES[item.status] ?? ''}`}
                >
                    {STATUS_OPTIONS.map(s => (
                        <option key={s} value={s}>{s.replace('_', ' ')}</option>
                    ))}
                </select>
            </div>
        </div>
    );
}

export default function RoadmapPage() {
    const [data, setData] = useState<RoadmapData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [updating, setUpdating] = useState<number | null>(null);
    const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});

    const fetchRoadmap = async () => {
        setLoading(true);
        setError(null);
        try {
            setData(await api.getRoadmap());
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error al cargar roadmap');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchRoadmap(); }, []);

    const handleStatusChange = async (id: number, newStatus: string) => {
        setUpdating(id);
        try {
            await api.updateRoadmapItem({ id, status: newStatus });
            await fetchRoadmap();
        } catch {
            // Silently fail — status will revert on refetch
        } finally {
            setUpdating(null);
        }
    };

    const togglePhase = (phase: number) => {
        setCollapsed(prev => ({ ...prev, [phase]: !prev[phase] }));
    };

    return (
        <div className="space-y-6">
            {/* Nav */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button asChild variant="ghost" size="sm">
                        <Link href="/">
                            <ArrowLeft className="w-4 h-4 mr-2" />
                            Volver
                        </Link>
                    </Button>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <Rocket className="w-8 h-8" />
                        Expansion Roadmap
                    </h1>
                </div>
                <Button variant="outline" size="sm" onClick={fetchRoadmap} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Actualizar
                </Button>
            </div>

            {/* Error */}
            {error && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-lg border border-destructive/20">
                    <p>{error}</p>
                    <Button variant="outline" size="sm" className="mt-2" onClick={fetchRoadmap}>
                        Reintentar
                    </Button>
                </div>
            )}

            {/* Summary cards */}
            {data && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <Card>
                        <CardContent className="pt-6 text-center">
                            <p className="text-3xl font-bold tabular-nums">{data.summary.total_items}</p>
                            <p className="text-xs text-muted-foreground">Total Items</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6 text-center">
                            <p className="text-3xl font-bold text-green-600 tabular-nums">{data.summary.completed}</p>
                            <p className="text-xs text-muted-foreground">Completados</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6 text-center">
                            <p className="text-3xl font-bold text-blue-600 tabular-nums">{data.summary.in_progress}</p>
                            <p className="text-xs text-muted-foreground">En Progreso</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6 text-center">
                            <p className="text-3xl font-bold tabular-nums">
                                {data.summary.total_estimated_laws.toLocaleString()}
                            </p>
                            <p className="text-xs text-muted-foreground">Leyes Estimadas</p>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Loading skeleton */}
            {loading && !data && (
                <div className="space-y-4">
                    {[1, 2, 3].map(i => (
                        <Card key={i} className="animate-pulse">
                            <CardContent className="pt-6"><div className="h-24 bg-muted rounded" /></CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Phase sections */}
            {data?.phases.map(phase => (
                <Card key={phase.phase}>
                    <CardHeader
                        className="pb-3 cursor-pointer select-none"
                        onClick={() => togglePhase(phase.phase)}
                    >
                        <div className="flex items-center gap-3">
                            {collapsed[phase.phase]
                                ? <ChevronRight className="w-5 h-5 text-muted-foreground" />
                                : <ChevronDown className="w-5 h-5 text-muted-foreground" />
                            }
                            <div className="flex-1 min-w-0">
                                <CardTitle className="text-lg">
                                    Fase {phase.phase}: {phase.label}
                                </CardTitle>
                                <div className="flex items-center gap-3 mt-1">
                                    <PhaseProgressBar phase={phase} />
                                    <span className="text-xs text-muted-foreground shrink-0">
                                        ~{phase.estimated_laws.toLocaleString()} leyes
                                    </span>
                                </div>
                            </div>
                        </div>
                    </CardHeader>
                    {!collapsed[phase.phase] && (
                        <CardContent className="space-y-1 pt-0">
                            {phase.items.map(item => (
                                <RoadmapItemRow
                                    key={item.id}
                                    item={item}
                                    onStatusChange={handleStatusChange}
                                    updating={updating}
                                />
                            ))}
                        </CardContent>
                    )}
                </Card>
            ))}
        </div>
    );
}
