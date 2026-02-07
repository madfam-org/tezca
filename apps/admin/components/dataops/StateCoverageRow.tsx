import { Badge } from "@tezca/ui";
import type { StateCoverage } from './types';

interface StateCoverageRowProps {
  row: StateCoverage;
}

function qualityColor(total: number): string {
  if (total >= 500) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
  if (total >= 100) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
}

function qualityLabel(total: number): string {
  if (total >= 500) return 'Buena';
  if (total >= 100) return 'Media';
  return 'Baja';
}

export function StateCoverageRow({ row }: StateCoverageRowProps) {
  return (
    <tr className="border-b border-muted/50 hover:bg-muted/30 transition-colors">
      <td className="py-2 px-3 text-sm font-medium">
        {row.state}
        {row.anomaly && (
          <Badge variant="destructive" className="ml-2 text-xs px-1.5 py-0">
            anomalía
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
      <td className="py-2 px-3">
        <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${qualityColor(row.total_in_db)}`}>
          {qualityLabel(row.total_in_db)}
        </span>
      </td>
      <td className="py-2 px-3 text-xs text-muted-foreground max-w-[200px] truncate">
        {row.anomaly}
      </td>
    </tr>
  );
}
