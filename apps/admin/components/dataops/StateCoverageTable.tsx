'use client';

import { useState, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "@tezca/ui";
import { Map, ArrowUpDown } from 'lucide-react';
import type { StateCoverage } from './types';
import { StateCoverageRow } from './StateCoverageRow';

interface StateCoverageTableProps {
  states: StateCoverage[];
}

type SortKey = 'state' | 'legislative_in_db' | 'non_legislative_in_db' | 'total_in_db';

export function StateCoverageTable({ states }: StateCoverageTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('state');
  const [sortAsc, setSortAsc] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...states];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return copy;
  }, [states, sortKey, sortAsc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(key === 'state');
    }
  };

  const sortTh = (label: string, colKey: SortKey) => (
    <th
      key={colKey}
      className="py-2 px-3 text-xs font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors"
      onClick={() => toggleSort(colKey)}
    >
      <span className="flex items-center gap-1 justify-end">
        {label}
        <ArrowUpDown className="w-3 h-3" />
      </span>
    </th>
  );

  const totalLeg = states.reduce((s, r) => s + r.legislative_in_db, 0);
  const totalNonLeg = states.reduce((s, r) => s + r.non_legislative_in_db, 0);
  const totalAll = states.reduce((s, r) => s + r.total_in_db, 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Map className="w-5 h-5" />
          Cobertura por Estado ({states.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-muted">
                <th
                  className="py-2 px-3 text-xs font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground"
                  onClick={() => toggleSort('state')}
                >
                  <span className="flex items-center gap-1">
                    Estado <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                {sortTh("Legislativo", "legislative_in_db")}
                {sortTh("No Legislativo", "non_legislative_in_db")}
                {sortTh("Total", "total_in_db")}
                <th className="py-2 px-3 text-xs font-medium text-muted-foreground">Anomalia</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(row => (
                <StateCoverageRow key={row.state} row={row} />
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-muted font-semibold">
                <td className="py-2 px-3 text-sm">Total</td>
                <td className="py-2 px-3 text-sm text-right tabular-nums">{totalLeg.toLocaleString()}</td>
                <td className="py-2 px-3 text-sm text-right tabular-nums">{totalNonLeg.toLocaleString()}</td>
                <td className="py-2 px-3 text-sm text-right tabular-nums">{totalAll.toLocaleString()}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
