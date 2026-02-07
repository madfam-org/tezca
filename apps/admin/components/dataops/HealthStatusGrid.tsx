'use client';

import { Card, CardHeader, CardTitle, CardContent } from "@tezca/ui";
import { Activity } from 'lucide-react';
import type { HealthStatus } from './types';
import { SourceHealthCard } from './SourceHealthCard';

interface HealthStatusGridProps {
  health: HealthStatus;
}

export function HealthStatusGrid({ health }: HealthStatusGridProps) {
  const { summary, sources } = health;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Salud de Fuentes
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary row */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 text-center">
          <div>
            <p className="text-xl font-bold tabular-nums">{summary.total_sources}</p>
            <p className="text-[10px] text-muted-foreground">Total</p>
          </div>
          <div>
            <p className="text-xl font-bold text-green-600 tabular-nums">{summary.healthy}</p>
            <p className="text-[10px] text-muted-foreground">OK</p>
          </div>
          <div>
            <p className="text-xl font-bold text-yellow-600 tabular-nums">{summary.degraded}</p>
            <p className="text-[10px] text-muted-foreground">Degradadas</p>
          </div>
          <div>
            <p className="text-xl font-bold text-red-600 tabular-nums">{summary.down}</p>
            <p className="text-[10px] text-muted-foreground">Caidas</p>
          </div>
          <div>
            <p className="text-xl font-bold text-gray-500 tabular-nums">{summary.unknown}</p>
            <p className="text-[10px] text-muted-foreground">Desconocido</p>
          </div>
          <div>
            <p className="text-xl font-bold text-gray-400 tabular-nums">{summary.never_checked}</p>
            <p className="text-[10px] text-muted-foreground">Sin verificar</p>
          </div>
        </div>

        {/* Source cards grid */}
        {sources.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {sources.map(src => (
              <SourceHealthCard key={src.id} source={src} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
