'use client';

import { useState, useRef, useCallback, lazy, Suspense } from 'react';
import { useLang } from '@/components/providers/LanguageContext';
import { useGraphData } from './useGraphData';
import { GraphControls } from './GraphControls';
import { GraphLegend } from './GraphLegend';
import { Network } from 'lucide-react';

const LawGraph = lazy(() => import('./LawGraph').then(m => ({ default: m.LawGraph })));

const content = {
    es: {
        title: 'Grafo de referencias',
        overviewTitle: 'Red de leyes',
        loading: 'Cargando grafo...',
        error: 'No se pudo cargar el grafo',
        empty: 'No hay referencias suficientes para visualizar',
        nodes: 'nodos',
        edges: 'aristas',
        truncated: '(truncado)',
    },
    en: {
        title: 'Reference graph',
        overviewTitle: 'Law network',
        loading: 'Loading graph...',
        error: 'Could not load the graph',
        empty: 'Not enough references to visualize',
        nodes: 'nodes',
        edges: 'edges',
        truncated: '(truncated)',
    },
    nah: {
        title: 'Tlanōnotzaliztli grafo',
        overviewTitle: 'Tenahuatilli mātlahtli',
        loading: 'Motēmoa grafo...',
        error: 'Ahmo huelītic in grafo',
        empty: 'Ahmo ixachi tlanōnotzaliztli',
        nodes: 'yahualli',
        edges: 'tlahuilōlli',
        truncated: '(tzontecomatl)',
    },
};

interface LawGraphContainerProps {
    lawId?: string;
}

export function LawGraphContainer({ lawId }: LawGraphContainerProps) {
    const { lang } = useLang();
    const t = content[lang];
    const containerRef = useRef<HTMLDivElement>(null);

    const [depth, setDepth] = useState(1);
    const [direction, setDirection] = useState('both');
    const [minConfidence, setMinConfidence] = useState(0.5);
    const [isFullscreen, setIsFullscreen] = useState(false);

    const { graph, loading, error } = useGraphData({
        lawId,
        depth: lawId ? depth : undefined,
        min_confidence: lawId ? minConfidence : undefined,
        direction: lawId ? direction : undefined,
        max_nodes: lawId ? 150 : 300,
        min_weight: lawId ? undefined : 3,
    });

    const toggleFullscreen = useCallback(() => {
        if (!containerRef.current) return;
        if (!document.fullscreenElement) {
            containerRef.current.requestFullscreen().catch(() => {});
            setIsFullscreen(true);
        } else {
            document.exitFullscreen().catch(() => {});
            setIsFullscreen(false);
        }
    }, []);

    const title = lawId ? t.title : t.overviewTitle;

    return (
        <section
            ref={containerRef}
            className={`mt-6 rounded-lg border bg-card p-4 shadow-sm ${isFullscreen ? 'bg-background' : ''}`}
        >
            <div className="flex items-center gap-2 mb-3">
                <Network className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">{title}</h3>
                {graph && !loading && (
                    <span className="text-xs text-muted-foreground ml-auto">
                        {graph.meta.total_nodes} {t.nodes}, {graph.meta.total_edges} {t.edges}
                        {graph.meta.truncated ? ` ${t.truncated}` : ''}
                    </span>
                )}
            </div>

            {lawId && (
                <div className="mb-3">
                    <GraphControls
                        depth={depth}
                        direction={direction}
                        minConfidence={minConfidence}
                        isFullscreen={isFullscreen}
                        onDepthChange={setDepth}
                        onDirectionChange={setDirection}
                        onConfidenceChange={setMinConfidence}
                        onToggleFullscreen={toggleFullscreen}
                    />
                </div>
            )}

            {loading && (
                <div className="flex items-center justify-center h-[400px] text-sm text-muted-foreground">
                    <div className="animate-pulse">{t.loading}</div>
                </div>
            )}

            {error && !loading && (
                <div className="flex items-center justify-center h-[400px] text-sm text-destructive">
                    {t.error}
                </div>
            )}

            {!loading && !error && graph && graph.nodes.length === 0 && (
                <div className="flex items-center justify-center h-[400px] text-sm text-muted-foreground">
                    {t.empty}
                </div>
            )}

            {!loading && !error && graph && graph.nodes.length > 0 && (
                <Suspense fallback={
                    <div className="flex items-center justify-center h-[400px] text-sm text-muted-foreground">
                        <div className="animate-pulse">{t.loading}</div>
                    </div>
                }>
                    <LawGraph data={graph} />
                </Suspense>
            )}

            <div className="mt-3">
                <GraphLegend />
            </div>
        </section>
    );
}
