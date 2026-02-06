'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { DashboardStats } from '@/lib/types';
import { Card, CardContent } from '@/components/ui/card';
import { BookOpen, Scale, Building2, Calendar, FileText, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';

export function DashboardStatsGrid() {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getStats()
            .then(setStats)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return <div className="animate-pulse space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-24 rounded-xl bg-muted" />
                ))}
            </div>
        </div>;
    }

    if (!stats) return <p className="text-center text-muted-foreground">No se pudieron cargar las estadísticas.</p>;

    return (
        <div className="space-y-8">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:grid-cols-4">
                <StatCard
                    label="Total de Leyes"
                    value={stats.total_laws.toLocaleString()}
                    icon={<BookOpen aria-hidden="true" className="h-5 w-5 text-primary" />}
                />
                <StatCard
                    label="Federales"
                    value={stats.federal_count.toLocaleString()}
                    icon={<Scale aria-hidden="true" className="h-5 w-5 text-blue-500" />}
                />
                <StatCard
                    label="Estatales"
                    value={stats.state_count.toLocaleString()}
                    icon={<Building2 aria-hidden="true" className="h-5 w-5 text-green-500" />}
                />
                <StatCard
                    label="Última Actualización"
                    value={stats.last_update ? new Date(stats.last_update).toLocaleDateString('es-MX') : '-'}
                    icon={<Calendar aria-hidden="true" className="h-5 w-5 text-orange-500" />}
                />
            </div>
        </div>
    );
}

function StatCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
    return (
        <Card>
            <CardContent className="flex flex-col items-center justify-center p-6 text-center">
                <div className="mb-3 rounded-full bg-secondary/30 p-2.5">
                    {icon}
                </div>
                <div className="text-2xl font-bold tracking-tight">{value}</div>
                <p className="text-xs font-medium text-muted-foreground">{label}</p>
            </CardContent>
        </Card>
    );
}

export function RecentLawsList() {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.getStats()
            .then(setStats)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="h-48 w-full animate-pulse rounded-xl bg-muted" />;
    if (!stats?.recent_laws.length) return null;

    return (
        <div className="rounded-xl border bg-card text-card-foreground shadow-sm">
            <div className="border-b p-6">
                <h3 className="font-semibold leading-none tracking-tight">
                    🔥 Actualizaciones Recientes
                </h3>
                <p className="text-sm text-muted-foreground mt-1.5">
                    Últimas leyes modificadas o publicadas en el DOF/Gacetas
                </p>
            </div>
            <div className="p-0">
                {stats.recent_laws.map((law, i) => (
                    <Link
                        key={law.id}
                        href={`/laws/${law.id}`}
                        className={`flex items-center justify-between p-4 transition-colors hover:bg-muted/50 ${i !== stats.recent_laws.length - 1 ? 'border-b' : ''
                            }`}
                    >
                        <div className="flex items-center gap-4 overflow-hidden">
                            <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <h4 className="truncate text-sm font-medium">
                                        {law.name}
                                    </h4>
                                    {isNew(law.date) && (
                                        <Badge variant="secondary" className="bg-success-50 text-success-700 dark:bg-success-700/15 dark:text-success-500 hover:bg-success-50 h-5 px-1.5 text-[10px]">
                                            NUEVO
                                        </Badge>
                                    )}
                                </div>
                                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                        <FileText className="h-3 w-3" />
                                        {law.tier === 'state' ? 'Estatal' : 'Federal'}
                                    </span>
                                    <span>•</span>
                                    <span>{new Date(law.date).toLocaleDateString('es-MX', { dateStyle: 'long' })}</span>
                                </div>
                            </div>
                        </div>
                        <ArrowRight className="h-4 w-4 text-muted-foreground/50" />
                    </Link>
                ))}
            </div>
            <div className="border-t p-4 text-center">
                <Link href="/search" className="text-sm font-medium text-primary hover:underline">
                    Ver todas las actualizaciones →
                </Link>
            </div>
        </div>
    );
}

function isNew(dateStr: string) {
    const date = new Date(dateStr);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays <= 30; // "New" if within last 30 days
}
