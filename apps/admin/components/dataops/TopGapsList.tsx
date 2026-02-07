'use client';

import { Badge } from "@tezca/ui";
import type { TopGap } from './types';

interface TopGapsListProps {
  gaps: TopGap[];
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
};

export function TopGapsList({ gaps }: TopGapsListProps) {
  if (!gaps.length) return null;

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Top 10 Brechas</p>
      <div className="space-y-1">
        {gaps.map(gap => (
          <div key={gap.id} className="flex items-start gap-2 text-xs p-1.5 rounded hover:bg-muted/50">
            <Badge
              variant="outline"
              className={`shrink-0 text-[10px] px-1.5 py-0 ${STATUS_COLORS[gap.status] ?? ''}`}
            >
              P{gap.priority}
            </Badge>
            <span className="text-muted-foreground shrink-0">{gap.state || gap.level}</span>
            <span className="truncate">{gap.description}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
