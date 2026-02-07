'use client';

import { Badge } from "@tezca/ui";
import type { StateCoverage } from './types';

interface StateCoverageRowProps {
  row: StateCoverage;
}

export function StateCoverageRow({ row }: StateCoverageRowProps) {
  return (
    <tr className="border-b border-muted/50 hover:bg-muted/30 transition-colors">
      <td className="py-2 px-3 text-sm font-medium">
        {row.state}
        {row.anomaly && (
          <Badge variant="destructive" className="ml-2 text-[10px] px-1.5 py-0">
            anomalia
          </Badge>
        )}
      </td>
      <td className="py-2 px-3 text-sm text-right tabular-nums">
        {row.legislative_in_db.toLocaleString()}
      </td>
      <td className="py-2 px-3 text-sm text-right tabular-nums">
        {row.non_legislative_in_db.toLocaleString()}
      </td>
      <td className="py-2 px-3 text-sm text-right tabular-nums font-semibold">
        {row.total_in_db.toLocaleString()}
      </td>
      <td className="py-2 px-3 text-xs text-muted-foreground max-w-[200px] truncate">
        {row.anomaly}
      </td>
    </tr>
  );
}
