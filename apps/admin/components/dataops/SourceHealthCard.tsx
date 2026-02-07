'use client';

import { Badge } from "@tezca/ui";
import type { HealthSource } from './types';

interface SourceHealthCardProps {
  source: HealthSource;
}

const STATUS_STYLES: Record<string, string> = {
  healthy: 'border-green-300 dark:border-green-800',
  degraded: 'border-yellow-300 dark:border-yellow-800',
  down: 'border-red-300 dark:border-red-800',
  unknown: 'border-gray-300 dark:border-gray-700',
};

const STATUS_BADGE: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  healthy: 'default',
  degraded: 'secondary',
  down: 'destructive',
  unknown: 'outline',
};

export function SourceHealthCard({ source }: SourceHealthCardProps) {
  const borderClass = STATUS_STYLES[source.status] ?? STATUS_STYLES.unknown;

  return (
    <div className={`rounded-lg border-2 p-3 space-y-1 ${borderClass}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium truncate">{source.name}</p>
        <Badge variant={STATUS_BADGE[source.status] ?? 'outline'} className="text-[10px] shrink-0">
          {source.status}
        </Badge>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>{source.level}</span>
        {source.response_time_ms != null && (
          <span>{source.response_time_ms}ms</span>
        )}
      </div>
      {source.last_check && (
        <p className="text-[10px] text-muted-foreground">
          Verificado: {new Date(source.last_check).toLocaleDateString('es-MX')}
        </p>
      )}
    </div>
  );
}
