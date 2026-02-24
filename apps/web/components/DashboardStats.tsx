'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { DashboardStats } from '@tezca/lib';
import { Card, CardContent, Badge } from '@tezca/ui';
import { BookOpen, Scale, Building2, Calendar, FileText, ArrowRight, Landmark, Briefcase } from 'lucide-react';
import Link from 'next/link';
import { useLang, LOCALE_MAP } from '@/components/providers/LanguageContext';

// Shared stats promise — deduplicates /stats/ calls across Hero, DashboardStatsGrid, RecentLawsList
let _statsPromise: Promise<DashboardStats> | null = null;

export function getSharedStats(): Promise<DashboardStats> {
    if (!_statsPromise) {
        _statsPromise = api.getStats();
        // Allow refetch after 5 minutes
        setTimeout(() => { _statsPromise = null; }, 5 * 60 * 1000);
    }
    return _statsPromise;
}

/** Reset the cached promise. Exported for tests only. */
export function _resetStatsCache() {
    _statsPromise = null;
}

const content = {
    es: {
        loadError: 'No se pudieron cargar las estadísticas.',
        totalLaws: 'Total de Leyes',
        federal: 'Federales',
        state: 'Estatales',
        legislative: 'Legislativas',
        nonLegislative: 'No Legislativas',
        lastUpdate: 'Última Actualización',
        recentTitle: 'Actualizaciones Recientes',
        recentDesc: 'Últimas leyes modificadas o publicadas en el DOF/Gacetas',
        new: 'NUEVO',
        tierState: 'Estatal',
        tierFederal: 'Federal',
        viewAll: 'Ver todas las actualizaciones →',
    },
    en: {
        loadError: 'Could not load statistics.',
        totalLaws: 'Total Laws',
        federal: 'Federal',
        state: 'State',
        legislative: 'Legislative',
        nonLegislative: 'Non-Legislative',
        lastUpdate: 'Last Update',
        recentTitle: 'Recent Updates',
        recentDesc: 'Latest laws modified or published in the DOF/Gazettes',
        new: 'NEW',
        tierState: 'State',
        tierFederal: 'Federal',
        viewAll: 'View all updates →',
    },
    nah: {
        loadError: 'Ahmo huelītic in tlanextīliztli.',
        totalLaws: 'Mochi Tenahuatilli',
        federal: 'Federal',
        state: 'Altepetl',
        legislative: 'Tenahuatīlli',
        nonLegislative: 'Ahmo Tenahuatīlli',
        lastUpdate: 'Tlāmian Yancuīliztli',
        recentTitle: 'Yancuīc Tlanemilīlli',
        recentDesc: 'Tlāmian tenahuatilli ōmopātih DOF/Gacetas',
        new: 'YANCUĪC',
        tierState: 'Altepetl',
        tierFederal: 'Federal',
        viewAll: 'Xiquitta mochi yancuīliztli →',
    },
};

export function DashboardStatsGrid() {
    const { lang } = useLang();
    const t = content[lang];
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const locale = LOCALE_MAP[lang];

    useEffect(() => {
        getSharedStats()
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

    if (!stats) return <p className="text-center text-muted-foreground">{t.loadError}</p>;

    return (
        <div className="space-y-8">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-6">
                <StatCard
                    label={t.totalLaws}
                    value={stats.total_laws.toLocaleString(locale)}
                    icon={<BookOpen aria-hidden="true" className="h-5 w-5 text-primary" />}
                />
                <StatCard
                    label={t.federal}
                    value={stats.federal_count.toLocaleString(locale)}
                    icon={<Scale aria-hidden="true" className="h-5 w-5 text-blue-500" />}
                />
                <StatCard
                    label={t.state}
                    value={stats.state_count.toLocaleString(locale)}
                    icon={<Building2 aria-hidden="true" className="h-5 w-5 text-green-500" />}
                />
                <StatCard
                    label={t.legislative}
                    value={(stats.legislative_count ?? 0).toLocaleString(locale)}
                    icon={<Landmark aria-hidden="true" className="h-5 w-5 text-indigo-500" />}
                />
                <StatCard
                    label={t.nonLegislative}
                    value={(stats.non_legislative_count ?? 0).toLocaleString(locale)}
                    icon={<Briefcase aria-hidden="true" className="h-5 w-5 text-amber-500" />}
                />
                <StatCard
                    label={t.lastUpdate}
                    value={stats.last_update ? new Date(stats.last_update).toLocaleDateString(locale) : '-'}
                    icon={<Calendar aria-hidden="true" className="h-5 w-5 text-orange-500" />}
                />
            </div>
        </div>
    );
}

function StatCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
    return (
        <Card>
            <CardContent className="flex flex-col items-center justify-center p-3 sm:p-6 text-center">
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
    const { lang } = useLang();
    const t = content[lang];
    const locale = LOCALE_MAP[lang];
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getSharedStats()
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
                    {t.recentTitle}
                </h3>
                <p className="text-sm text-muted-foreground mt-1.5">
                    {t.recentDesc}
                </p>
            </div>
            <div className="p-0">
                {stats.recent_laws.map((law, i) => (
                    <Link
                        key={law.id}
                        href={`/leyes/${law.id}`}
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
                                            {t.new}
                                        </Badge>
                                    )}
                                </div>
                                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                        <FileText className="h-3 w-3" />
                                        {law.tier === 'state' ? t.tierState : t.tierFederal}
                                    </span>
                                    <span>•</span>
                                    <span>{new Date(law.date).toLocaleDateString(locale, { dateStyle: 'long' })}</span>
                                </div>
                            </div>
                        </div>
                        <ArrowRight className="h-4 w-4 text-muted-foreground/50" />
                    </Link>
                ))}
            </div>
            <div className="border-t p-4 text-center">
                <Link href="/busqueda" className="text-sm font-medium text-primary hover:underline">
                    {t.viewAll}
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
