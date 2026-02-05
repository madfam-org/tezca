'use client';

import { useEffect, useState } from 'react';
import { MetricCard } from './MetricCard';
import { BookOpen, Award, Activity, Clock, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';

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
            // Try to fetch from API, fallback to mock data if it fails
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/api/v1/admin/metrics/`);
            
            if (!response.ok) throw new Error('API not available');
            
            const data = await response.json();
            setMetrics(data);
            setError(null);
        } catch (err) {
            console.warn('Using fallback metrics data:', err);
            // Fallback to mock data for development
            setMetrics({
                totalLaws: 11667,
                federalLaws: 330,
                stateLaws: 11337,
                gradeA: 87,
                gradeB: 11,
                activeJobs: 0,
                lastUpdate: new Date().toISOString(),
                lawsTrend: '+120',
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMetrics();
        
        // Refresh every 30 seconds
        const interval = setInterval(fetchMetrics, 30000);
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
