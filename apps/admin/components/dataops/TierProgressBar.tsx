'use client';

import { Badge } from "@tezca/ui";
import type { TierProgress } from './types';

interface TierProgressBarProps {
  tier: TierProgress;
}

function pctColor(pct: number): string {
  if (pct >= 90) return 'bg-green-500';
  if (pct >= 50) return 'bg-yellow-500';
  if (pct > 0) return 'bg-orange-500';
  return 'bg-gray-300';
}

function confidenceBadge(c: string) {
  const variant = c === 'high' ? 'default' : c === 'medium' ? 'secondary' : 'outline';
  return <Badge variant={variant} className="text-[10px] px-1.5 py-0">{c}</Badge>;
}

export function TierProgressBar({ tier }: TierProgressBarProps) {
  const universe = tier.known_universe;
  const pct = tier.coverage_pct;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-medium truncate">{tier.label}</span>
          {confidenceBadge(tier.confidence)}
        </div>
        <div className="flex items-center gap-2 text-muted-foreground text-xs shrink-0">
          <span>{tier.in_db.toLocaleString()} en BD</span>
          {universe != null && (
            <span>/ {universe.toLocaleString()}</span>
          )}
          <span className="font-semibold text-foreground">{pct}%</span>
        </div>
      </div>
      <div className="h-2.5 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pctColor(pct)}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      {tier.permanent_gaps > 0 && (
        <p className="text-xs text-muted-foreground">
          {tier.permanent_gaps.toLocaleString()} brechas permanentes
        </p>
      )}
    </div>
  );
}
