'use client';

import { useLang } from '@/components/providers/LanguageContext';
import { trackEvent } from '@/lib/analytics/posthog';
import { ZoomIn, ZoomOut, Maximize2, Minimize2, RotateCcw, Play, Pause, Download } from 'lucide-react';

const content = {
    es: {
        depth: 'Profundidad',
        direction: 'Dirección',
        both: 'Ambas',
        outgoing: 'Salientes',
        incoming: 'Entrantes',
        confidence: 'Confianza mín.',
        fullscreen: 'Pantalla completa',
        exitFullscreen: 'Salir',
        resetView: 'Restablecer vista',
        pauseLayout: 'Pausar simulación',
        playLayout: 'Reanudar simulación',
        exportPNG: 'Exportar PNG',
    },
    en: {
        depth: 'Depth',
        direction: 'Direction',
        both: 'Both',
        outgoing: 'Outgoing',
        incoming: 'Incoming',
        confidence: 'Min confidence',
        fullscreen: 'Fullscreen',
        exitFullscreen: 'Exit',
        resetView: 'Reset view',
        pauseLayout: 'Pause simulation',
        playLayout: 'Resume simulation',
        exportPNG: 'Export PNG',
    },
    nah: {
        depth: 'Huehcatl',
        direction: 'Tlanextiliztli',
        both: 'Ōmextin',
        outgoing: 'Quīzqui',
        incoming: 'Calaqui',
        confidence: 'Tlaneltoquiliztli',
        fullscreen: 'Huēyi',
        exitFullscreen: 'Quīza',
        resetView: 'Xicpēhua',
        pauseLayout: 'Xictzicoa',
        playLayout: 'Xicnēltoca',
        exportPNG: 'Xicquīxtia PNG',
    },
};

interface GraphControlsProps {
    depth: number;
    direction: string;
    minConfidence: number;
    isFullscreen: boolean;
    layoutRunning?: boolean;
    onDepthChange: (d: number) => void;
    onDirectionChange: (d: string) => void;
    onConfidenceChange: (c: number) => void;
    onZoomIn?: () => void;
    onZoomOut?: () => void;
    onToggleFullscreen: () => void;
    onResetView?: () => void;
    onToggleLayout?: () => void;
    onExportPNG?: () => void;
    floating?: boolean;
}

export function GraphControls({
    depth,
    direction,
    minConfidence,
    isFullscreen,
    layoutRunning,
    onDepthChange,
    onDirectionChange,
    onConfidenceChange,
    onZoomIn,
    onZoomOut,
    onToggleFullscreen,
    onResetView,
    onToggleLayout,
    onExportPNG,
    floating,
}: GraphControlsProps) {
    const { lang } = useLang();
    const t = content[lang];

    const btnClass = 'rounded-md p-1.5 hover:bg-muted transition-colors';

    const wrapperClass = floating
        ? 'absolute top-3 left-3 z-10 flex flex-wrap items-center gap-3 text-sm rounded-lg border bg-card/90 backdrop-blur-sm p-2 shadow-md'
        : 'flex flex-wrap items-center gap-3 text-sm';

    return (
        <div className={wrapperClass}>
            {/* Depth selector */}
            <label className="inline-flex items-center gap-1.5">
                <span className="text-muted-foreground">{t.depth}:</span>
                <select
                    value={depth}
                    onChange={(e) => onDepthChange(Number(e.target.value))}
                    className="rounded-md border bg-background px-2 py-1 text-sm"
                >
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                </select>
            </label>

            {/* Direction toggle */}
            <label className="inline-flex items-center gap-1.5">
                <span className="text-muted-foreground">{t.direction}:</span>
                <select
                    value={direction}
                    onChange={(e) => onDirectionChange(e.target.value)}
                    className="rounded-md border bg-background px-2 py-1 text-sm"
                >
                    <option value="both">{t.both}</option>
                    <option value="outgoing">{t.outgoing}</option>
                    <option value="incoming">{t.incoming}</option>
                </select>
            </label>

            {/* Confidence slider */}
            <label className="inline-flex items-center gap-1.5">
                <span className="text-muted-foreground">{t.confidence}:</span>
                <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.1}
                    value={minConfidence}
                    onChange={(e) => onConfidenceChange(Number(e.target.value))}
                    className="w-20"
                />
                <span className="text-xs text-muted-foreground w-6">{minConfidence}</span>
            </label>

            {/* Action buttons */}
            <div className="flex items-center gap-1 ml-auto">
                {onToggleLayout && (
                    <button
                        onClick={onToggleLayout}
                        className={btnClass}
                        aria-label={layoutRunning ? t.pauseLayout : t.playLayout}
                    >
                        {layoutRunning ? (
                            <Pause className="h-4 w-4" />
                        ) : (
                            <Play className="h-4 w-4" />
                        )}
                    </button>
                )}
                {onResetView && (
                    <button
                        onClick={onResetView}
                        className={btnClass}
                        aria-label={t.resetView}
                    >
                        <RotateCcw className="h-4 w-4" />
                    </button>
                )}
                {onExportPNG && (
                    <button
                        onClick={() => { onExportPNG(); trackEvent('graph.exported_png'); }}
                        className={btnClass}
                        aria-label={t.exportPNG}
                    >
                        <Download className="h-4 w-4" />
                    </button>
                )}
                {onZoomIn && (
                    <button
                        onClick={onZoomIn}
                        className={btnClass}
                        aria-label="Zoom in"
                    >
                        <ZoomIn className="h-4 w-4" />
                    </button>
                )}
                {onZoomOut && (
                    <button
                        onClick={onZoomOut}
                        className={btnClass}
                        aria-label="Zoom out"
                    >
                        <ZoomOut className="h-4 w-4" />
                    </button>
                )}
                <button
                    onClick={onToggleFullscreen}
                    className={btnClass}
                    aria-label={isFullscreen ? t.exitFullscreen : t.fullscreen}
                >
                    {isFullscreen ? (
                        <Minimize2 className="h-4 w-4" />
                    ) : (
                        <Maximize2 className="h-4 w-4" />
                    )}
                </button>
            </div>
        </div>
    );
}
