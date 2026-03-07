'use client';

import { useLang } from '@/components/providers/LanguageContext';
import { ZoomIn, ZoomOut, Maximize2, Minimize2 } from 'lucide-react';

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
    },
};

interface GraphControlsProps {
    depth: number;
    direction: string;
    minConfidence: number;
    isFullscreen: boolean;
    onDepthChange: (d: number) => void;
    onDirectionChange: (d: string) => void;
    onConfidenceChange: (c: number) => void;
    onZoomIn?: () => void;
    onZoomOut?: () => void;
    onToggleFullscreen: () => void;
}

export function GraphControls({
    depth,
    direction,
    minConfidence,
    isFullscreen,
    onDepthChange,
    onDirectionChange,
    onConfidenceChange,
    onZoomIn,
    onZoomOut,
    onToggleFullscreen,
}: GraphControlsProps) {
    const { lang } = useLang();
    const t = content[lang];

    return (
        <div className="flex flex-wrap items-center gap-3 text-sm">
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

            {/* Zoom + fullscreen */}
            <div className="flex items-center gap-1 ml-auto">
                {onZoomIn && (
                    <button
                        onClick={onZoomIn}
                        className="rounded-md p-1.5 hover:bg-muted transition-colors"
                        aria-label="Zoom in"
                    >
                        <ZoomIn className="h-4 w-4" />
                    </button>
                )}
                {onZoomOut && (
                    <button
                        onClick={onZoomOut}
                        className="rounded-md p-1.5 hover:bg-muted transition-colors"
                        aria-label="Zoom out"
                    >
                        <ZoomOut className="h-4 w-4" />
                    </button>
                )}
                <button
                    onClick={onToggleFullscreen}
                    className="rounded-md p-1.5 hover:bg-muted transition-colors"
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
