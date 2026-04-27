'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from './MetricCard';
import { BookOpen, Award, Activity, Clock, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import { ADMIN_METRICS_POLL_MS } from '@/lib/constants';

interface SystemMetrics {
    totalLaws: number;
    federalLaws: number;
    stateLaws: number;
    gradeA: number;
    gradeB: number;
    activeJobs: number;
    lastUpdate: string;
    lawsTrend: string;
}

export function SystemMetrics() {
    const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchMetrics = async () => {
        try {
            const data = await api.getAdminMetrics();
            
            setMetrics({
                totalLaws: data.total_laws,
                federalLaws: data.counts.federal,
                stateLaws: data.counts.state,
                gradeA: 0,
                gradeB: 0,
                activeJobs: 0,
                lastUpdate: data.last_updated,
                lawsTrend: '+0',
            });
            setError(null);
        } catch {
            setError('Error al cargar métricas');
            setMetrics(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMetrics();
        
        const interval = setInterval(fetchMetrics, ADMIN_METRICS_POLL_MS);
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return (
            <div className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-32 bg-muted animate-pulse rounded-lg" />
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
                {error}
            </div>
        );
    }

    if (!metrics) return null;

    const totalGradePercentage = ((metrics.gradeA + metrics.gradeB) / 100 * 100).toFixed(0);

    return (
        <div className="space-y-4 sm:space-y-6">
            <div className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                    title="Total Laws"
                    value={metrics.totalLaws.toLocaleString()}
                    trend={metrics.lawsTrend}
                    icon={BookOpen}
                    description={`${metrics.federalLaws} federal, ${metrics.stateLaws} state`}
                    status="info"
                />
                
                <MetricCard
                    title="High Quality"
                    value={`${totalGradePercentage}%`}
                    icon={Award}
                    description={`${metrics.gradeA}% Grade A, ${metrics.gradeB}% Grade B`}
                    status="success"
                />
                
                <MetricCard
                    title="Active Jobs"
                    value={metrics.activeJobs}
                    icon={Activity}
                    status={metrics.activeJobs > 0 ? 'warning' : 'success'}
                    description={metrics.activeJobs > 0 ? 'In progress' : 'All complete'}
                />
                
                <MetricCard
                    title="Last Update"
                    value={new Date(metrics.lastUpdate).toLocaleTimeString('es-MX', {
                        hour: '2-digit',
                        minute: '2-digit'
                    })}
                    icon={Clock}
                    description={new Date(metrics.lastUpdate).toLocaleDateString('es-MX', {
                        day: 'numeric',
                        month: 'short'
                    })}
                    status="info"
                />
            </div>

            <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2">
                <MetricCard
                    title="Growth Rate"
                    value={metrics.lawsTrend}
                    icon={TrendingUp}
                    description="Laws added this month"
                    status="success"
                />
                
                <MetricCard
                    title="Coverage"
                    value="33/33"
                    icon={BookOpen}
                    description="States + Federal jurisdiction"
                    status="success"
                />
            </div>
        </div>
    );
}
