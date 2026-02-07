'use client';

import { Badge } from "@tezca/ui";
import type { ExpansionPriority } from './types';

interface PriorityRowProps {
  item: ExpansionPriority;
}

const EFFORT_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  high: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

export function PriorityRow({ item }: PriorityRowProps) {
  return (
    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors">
      <span className="text-lg font-bold text-muted-foreground w-6 text-right shrink-0">
        #{item.rank}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">{item.action}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${EFFORT_COLORS[item.effort] ?? ''}`}>
            {item.effort}
          </Badge>
          {item.estimated_gain > 0 && (
            <span className="text-xs text-muted-foreground">
              +{item.estimated_gain.toLocaleString()} leyes
            </span>
          )}
        </div>
      </div>
      <div className="text-right shrink-0">
        <p className="text-sm font-semibold">{item.roi_score}</p>
        <p className="text-[10px] text-muted-foreground">ROI</p>
      </div>
    </div>
  );
}
