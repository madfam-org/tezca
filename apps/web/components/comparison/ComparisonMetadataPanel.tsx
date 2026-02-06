'use client';

import { Badge } from "@leyesmx/ui";
import type { ComparisonLawData } from './types';

interface ComparisonMetadataPanelProps {
    laws: ComparisonLawData[];
    matchCount: number;
}

function tierLabel(tier: number | string | undefined): string {
    if (tier === 'federal' || tier === 1) return 'Federal';
    if (tier === 'state' || tier === 2) return 'Estatal';
    if (tier === 'municipal' || tier === 3) return 'Municipal';
    return 'Desconocido';
}

function tierVariant(tier: number | string | undefined): 'default' | 'secondary' | 'outline' {
    if (tier === 'federal' || tier === 1) return 'default';
    if (tier === 'state' || tier === 2) return 'secondary';
    return 'outline';
}

export function ComparisonMetadataPanel({ laws, matchCount }: ComparisonMetadataPanelProps) {
    if (laws.length < 2) return null;

    return (
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 sm:gap-4 px-4 sm:px-6 py-3 sm:py-4 border-b bg-muted/20">
            {/* Law A */}
            <MetadataCard law={laws[0]} />

            {/* Center stats */}
            <div className="hidden sm:flex flex-col items-center justify-center px-4 text-center">
                <span className="text-2xl font-bold text-primary">{matchCount}</span>
                <span className="text-xs text-muted-foreground">
                    {matchCount === 1 ? 'artículo en común' : 'artículos en común'}
                </span>
            </div>

            {/* Law B */}
            <MetadataCard law={laws[1]} />

            {/* Mobile center stats */}
            <div className="sm:hidden text-center py-2 border-t">
                <span className="text-lg font-bold text-primary">{matchCount}</span>
                <span className="text-xs text-muted-foreground ml-1">
                    {matchCount === 1 ? 'artículo en común' : 'artículos en común'}
                </span>
            </div>
        </div>
    );
}

function MetadataCard({ law }: { law: ComparisonLawData }) {
    return (
        <div className="rounded-lg border bg-card p-3 space-y-1.5">
            <h3 className="text-sm font-semibold truncate" title={law.meta.name}>
                {law.meta.name}
            </h3>
            <div className="flex flex-wrap gap-1.5">
                <Badge variant={tierVariant(law.meta.tier)}>
                    {tierLabel(law.meta.tier)}
                </Badge>
                {law.meta.category && (
                    <Badge variant="outline" className="text-xs">
                        {law.meta.category}
                    </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                    {law.details.total} artículos
                </Badge>
            </div>
        </div>
    );
}
