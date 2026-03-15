'use client';

import { useState, useRef, useCallback, lazy, Suspense, useMemo } from 'react';
import { useLang } from '@/components/providers/LanguageContext';
import { trackEvent } from '@/lib/analytics/posthog';
import { useGraphData } from './useGraphData';
import { GraphControls } from './GraphControls';
import { GraphLegend } from './GraphLegend';
import { GraphSearch } from './GraphSearch';
import { GraphStats } from './GraphStats';
import { GraphFilters } from './GraphFilters';
import { useGraphExport } from './useGraphExport';
import { type ColorMode, getUniqueCategories } from './graphConstants';
import { Network } from 'lucide-react';
import type Sigma from 'sigma';

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
    mode?: 'embedded' | 'fullscreen';
}

export function LawGraphContainer({ lawId, mode = 'embedded' }: LawGraphContainerProps) {
    const { lang } = useLang();
    const t = content[lang];
    const containerRef = useRef<HTMLDivElement>(null);
    const graphContainerRef = useRef<HTMLDivElement>(null);

    const [depth, setDepth] = useState(1);
    const [direction, setDirection] = useState('both');
    const [minConfidence, setMinConfidence] = useState(0.5);
    const [isFullscreen, setIsFullscreen] = useState(false);

    // Phase 1: Color mode + category filtering
    const [colorMode, setColorMode] = useState<ColorMode>('category');
    const [hiddenCategories, setHiddenCategories] = useState<Set<string>>(new Set());

    // Phase 2: Layout state
    const [layoutRunning, setLayoutRunning] = useState(false);

    // Phase 4: Focus node
    const [focusNodeFn, setFocusNodeFn] = useState<((nodeId: string) => void) | null>(null);

    const { graph, loading, error } = useGraphData({
        lawId,
        depth: lawId ? depth : undefined,
        min_confidence: lawId ? minConfidence : undefined,
        direction: lawId ? direction : undefined,
        max_nodes: lawId ? 150 : 300,
        min_weight: lawId ? undefined : 3,
    });

    // Unique categories from data
    const categories = useMemo(() =>
        graph ? getUniqueCategories(graph.nodes) : [],
    [graph]);

    // Search nodes list
    const searchNodes = useMemo(() =>
        graph ? graph.nodes.map(n => ({ id: n.id, label: n.label })) : [],
    [graph]);

    // Sigma getter for export
    const getSigma = useCallback((): Sigma | null => {
        const el = graphContainerRef.current?.querySelector('[style*="cursor"]') as HTMLDivElement | null;
        const controls = (el as HTMLDivElement & { __graphControls?: { getSigma: () => Sigma | null } })?.__graphControls;
        return controls?.getSigma() ?? null;
    }, []);

    const { exportPNG } = useGraphExport(getSigma);

    const toggleFullscreen = useCallback(() => {
        if (!containerRef.current) return;
        if (!document.fullscreenElement) {
            containerRef.current.requestFullscreen().catch(() => {});
            setIsFullscreen(true);
            trackEvent('graph.fullscreen_toggled', { is_fullscreen: true });
        } else {
            document.exitFullscreen().catch(() => {});
            setIsFullscreen(false);
            trackEvent('graph.fullscreen_toggled', { is_fullscreen: false });
        }
    }, []);

    const toggleCategory = useCallback((cat: string) => {
        setHiddenCategories(prev => {
            const next = new Set(prev);
            if (next.has(cat)) {
                next.delete(cat);
            } else {
                next.add(cat);
            }
            return next;
        });
    }, []);

    const showAllCategories = useCallback(() => {
        setHiddenCategories(new Set());
    }, []);

    const handleResetView = useCallback(() => {
        const el = graphContainerRef.current?.querySelector('[style*="cursor"]') as HTMLDivElement | null;
        const controls = (el as HTMLDivElement & { __graphControls?: { resetCamera: () => void } })?.__graphControls;
        controls?.resetCamera();
    }, []);

    const handleToggleLayout = useCallback(() => {
        const el = graphContainerRef.current?.querySelector('[style*="cursor"]') as HTMLDivElement | null;
        const controls = (el as HTMLDivElement & { __graphControls?: { toggleLayout: () => void } })?.__graphControls;
        controls?.toggleLayout();
    }, []);

    const handleClearFocus = useCallback(() => {
        const el = graphContainerRef.current?.querySelector('[style*="cursor"]') as HTMLDivElement | null;
        const controls = (el as HTMLDivElement & { __graphControls?: { clearFocus: () => void } })?.__graphControls;
        controls?.clearFocus();
    }, []);

    const isFullscreenMode = mode === 'fullscreen';
    const title = lawId ? t.title : t.overviewTitle;

    // Container height
    const graphContainerClass = isFullscreenMode
        ? 'w-full h-[calc(100dvh-64px)] rounded-lg border bg-background'
        : 'w-full h-[500px] sm:h-[600px] rounded-lg border bg-background';

    return (
        <section
            ref={containerRef}
            className={`${isFullscreenMode ? '' : 'mt-6 rounded-lg border bg-card p-4 shadow-sm'} ${isFullscreen ? 'bg-background' : ''}`}
        >
            {/* Header */}
            {!isFullscreenMode && (
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
            )}

            {/* Controls (for embedded law-specific mode) */}
            {lawId && !isFullscreenMode && (
                <div className="mb-3">
                    <GraphControls
                        depth={depth}
                        direction={direction}
                        minConfidence={minConfidence}
                        isFullscreen={isFullscreen}
                        layoutRunning={layoutRunning}
                        onDepthChange={setDepth}
                        onDirectionChange={setDirection}
                        onConfidenceChange={setMinConfidence}
                        onToggleFullscreen={toggleFullscreen}
                        onResetView={handleResetView}
                        onToggleLayout={handleToggleLayout}
                        onExportPNG={exportPNG}
                    />
                </div>
            )}

            {/* Loading state */}
            {loading && (
                <div className={`flex items-center justify-center ${isFullscreenMode ? 'h-[calc(100dvh-64px)]' : 'h-[500px] sm:h-[600px]'} text-sm text-muted-foreground`}>
                    <div className="animate-pulse">{t.loading}</div>
                </div>
            )}

            {/* Error state */}
            {error && !loading && (
                <div className={`flex items-center justify-center ${isFullscreenMode ? 'h-[calc(100dvh-64px)]' : 'h-[500px] sm:h-[600px]'} text-sm text-destructive`}>
                    {t.error}
                </div>
            )}

            {/* Empty state */}
            {!loading && !error && graph && graph.nodes.length === 0 && (
                <div className={`flex items-center justify-center ${isFullscreenMode ? 'h-[calc(100dvh-64px)]' : 'h-[500px] sm:h-[600px]'} text-sm text-muted-foreground`}>
                    {t.empty}
                </div>
            )}

            {/* Graph */}
            {!loading && !error && graph && graph.nodes.length > 0 && (
                <div ref={graphContainerRef} className="relative">
                    <Suspense fallback={
                        <div className={`flex items-center justify-center ${isFullscreenMode ? 'h-[calc(100dvh-64px)]' : 'h-[500px] sm:h-[600px]'} text-sm text-muted-foreground`}>
                            <div className="animate-pulse">{t.loading}</div>
                        </div>
                    }>
                        <LawGraph
                            data={graph}
                            colorMode={colorMode}
                            hiddenCategories={hiddenCategories}
                            containerClassName={graphContainerClass}
                            onFocusNodeRef={setFocusNodeFn}
                            onLayoutRunningChange={setLayoutRunning}
                        />
                    </Suspense>

                    {/* Floating overlays for fullscreen mode */}
                    {isFullscreenMode && (
                        <>
                            {/* Search */}
                            <GraphSearch
                                nodes={searchNodes}
                                onFocus={(nodeId) => focusNodeFn?.(nodeId)}
                                onClear={handleClearFocus}
                            />

                            {/* Stats */}
                            <GraphStats data={graph} floating />

                            {/* Filters */}
                            {categories.length > 1 && (
                                <GraphFilters
                                    categories={categories}
                                    hiddenCategories={hiddenCategories}
                                    onToggleCategory={toggleCategory}
                                    onShowAll={showAllCategories}
                                    floating
                                />
                            )}

                            {/* Layout running indicator */}
                            {layoutRunning && (
                                <div className="absolute bottom-3 right-3 z-10 flex items-center gap-1.5 rounded-full bg-card/90 backdrop-blur-sm px-3 py-1.5 text-xs text-muted-foreground shadow-sm border">
                                    <span className="inline-block w-2 h-2 rounded-full bg-primary animate-pulse" />
                                    {lang === 'es' ? 'Simulando...' : lang === 'en' ? 'Simulating...' : 'Motēmoa...'}
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* Legend */}
            <div className={isFullscreenMode ? 'absolute bottom-3 left-3 z-10' : 'mt-3'}>
                <GraphLegend
                    colorMode={colorMode}
                    onColorModeChange={setColorMode}
                    hiddenCategories={hiddenCategories}
                    onToggleCategory={toggleCategory}
                    categories={categories}
                    floating={isFullscreenMode}
                />
            </div>
        </section>
    );
}
