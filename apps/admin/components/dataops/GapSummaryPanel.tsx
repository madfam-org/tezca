'use client';

import { Card, CardHeader, CardTitle, CardContent } from "@tezca/ui";
import { AlertTriangle } from 'lucide-react';
import type { GapSummary } from './types';
import { GapTypeCard } from './GapTypeCard';
import { TopGapsList } from './TopGapsList';

interface GapSummaryPanelProps {
  gaps: GapSummary;
}

export function GapSummaryPanel({ gaps }: GapSummaryPanelProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          Brechas de Datos
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div>
            <p className="text-2xl font-bold tabular-nums">{gaps.total}</p>
            <p className="text-xs text-muted-foreground">Total</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-orange-600 tabular-nums">{gaps.actionable}</p>
            <p className="text-xs text-muted-foreground">Accionables</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-red-600 tabular-nums">{gaps.overdue}</p>
            <p className="text-xs text-muted-foreground">Vencidas</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-600 tabular-nums">
              {gaps.by_status?.resolved ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">Resueltas</p>
          </div>
        </div>

        {/* By type */}
        {Object.keys(gaps.by_type).length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Por Tipo</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(gaps.by_type).map(([type, count]) => (
                <GapTypeCard key={type} type={type} count={count} />
              ))}
            </div>
          </div>
        )}

        {/* Top gaps */}
        <TopGapsList gaps={gaps.top_gaps ?? []} />
      </CardContent>
    </Card>
  );
}
