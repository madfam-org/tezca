'use client';

import type { GraphNode } from '@/lib/api';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        refs: 'referencias',
        click: 'Clic para ver',
    },
    en: {
        refs: 'references',
        click: 'Click to view',
    },
    nah: {
        refs: 'tlanōnotzaliztli',
        click: 'Xiquitta',
    },
};

interface GraphTooltipProps {
    node: GraphNode | null;
    position: { x: number; y: number } | null;
}

export function GraphTooltip({ node, position }: GraphTooltipProps) {
    const { lang } = useLang();
    const t = content[lang];

    if (!node || !position) return null;

    return (
        <div
            className="pointer-events-none fixed z-50 rounded-md border bg-popover px-3 py-2 text-sm shadow-md"
            style={{ left: position.x + 12, top: position.y - 10 }}
        >
            <p className="font-medium text-foreground max-w-xs truncate">{node.label}</p>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
                {node.tier && (
                    <span className="inline-flex items-center rounded-full bg-muted px-1.5 py-0.5">
                        {node.tier}
                    </span>
                )}
                {node.category && (
                    <span className="inline-flex items-center rounded-full bg-muted px-1.5 py-0.5">
                        {node.category}
                    </span>
                )}
                <span>{node.ref_count} {t.refs}</span>
            </div>
            <p className="text-xs text-primary mt-1">{t.click}</p>
        </div>
    );
}
