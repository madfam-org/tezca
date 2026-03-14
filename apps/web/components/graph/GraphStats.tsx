'use client';

import { useMemo, useState } from 'react';
import { useLang } from '@/components/providers/LanguageContext';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { GraphResponse } from '@/lib/api';

const content = {
    es: {
        stats: 'Estadísticas',
        nodes: 'Nodos',
        edges: 'Aristas',
        mostConnected: 'Más conectada',
        avgConnections: 'Conexiones prom.',
        density: 'Densidad',
    },
    en: {
        stats: 'Statistics',
        nodes: 'Nodes',
        edges: 'Edges',
        mostConnected: 'Most connected',
        avgConnections: 'Avg. connections',
        density: 'Density',
    },
    nah: {
        stats: 'Tlapōhualli',
        nodes: 'Yahualli',
        edges: 'Tlahuilōlli',
        mostConnected: 'Ōcachi tlazōlli',
        avgConnections: 'Tlanepantla',
        density: 'Tetzāhuac',
    },
};

interface GraphStatsProps {
    data: GraphResponse;
    floating?: boolean;
}

export function GraphStats({ data, floating }: GraphStatsProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [collapsed, setCollapsed] = useState(true);

    const stats = useMemo(() => {
        const nodes = data.nodes;
        const edges = data.edges;
        const n = nodes.length;
        const e = edges.length;

        const mostConnected = nodes.reduce((best, node) =>
            node.ref_count > (best?.ref_count ?? 0) ? node : best
        , nodes[0]);

        const avgConnections = n > 0
            ? (nodes.reduce((sum, node) => sum + node.ref_count, 0) / n).toFixed(1)
            : '0';

        // Graph density: 2e / (n * (n-1)) for directed
        const density = n > 1
            ? ((2 * e) / (n * (n - 1))).toFixed(4)
            : '0';

        return { n, e, mostConnected, avgConnections, density };
    }, [data]);

    const wrapperClass = floating
        ? 'absolute top-3 right-3 z-10 rounded-lg border bg-card/90 backdrop-blur-sm shadow-md text-xs max-w-[calc(100vw-2rem)]'
        : 'rounded-lg border bg-card p-3 text-xs';

    return (
        <div className={wrapperClass}>
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="flex items-center gap-1.5 px-3 py-2 w-full text-left font-medium text-foreground"
            >
                {t.stats}
                {collapsed ? <ChevronDown className="h-3 w-3 ml-auto" /> : <ChevronUp className="h-3 w-3 ml-auto" />}
            </button>
            {!collapsed && (
                <div className="px-3 pb-2 space-y-1 text-muted-foreground">
                    <div className="flex justify-between">
                        <span>{t.nodes}</span>
                        <span className="font-medium text-foreground">{stats.n}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>{t.edges}</span>
                        <span className="font-medium text-foreground">{stats.e}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>{t.avgConnections}</span>
                        <span className="font-medium text-foreground">{stats.avgConnections}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>{t.density}</span>
                        <span className="font-medium text-foreground">{stats.density}</span>
                    </div>
                    {stats.mostConnected && (
                        <div className="pt-1 border-t border-border">
                            <span className="text-muted-foreground">{t.mostConnected}:</span>
                            <p className="font-medium text-foreground truncate">{stats.mostConnected.label}</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
