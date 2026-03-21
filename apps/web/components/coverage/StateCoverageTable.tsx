'use client';

import { useState, useMemo } from 'react';
import { Card, CardContent } from '@tezca/ui';
import { MapPin as MapIcon, ArrowUpDown } from 'lucide-react';

type Lang = 'es' | 'en' | 'nah';

interface StateCoverageRow {
  state: string;
  legislative: number;
  non_legislative: number;
  total: number;
}

interface StateCoverageTableProps {
  states: StateCoverageRow[];
  lang: Lang;
}

type SortKey = 'state' | 'legislative' | 'non_legislative' | 'total';

const columnLabels: Record<Lang, Record<string, string>> = {
  es: {
    title: 'Cobertura por estado',
    state: 'Estado',
    legislative: 'Legislativo',
    non_legislative: 'No legislativo',
    total: 'Total',
  },
  en: {
    title: 'Coverage by state',
    state: 'State',
    legislative: 'Legislative',
    non_legislative: 'Non-legislative',
    total: 'Total',
  },
  nah: {
    title: 'Altepetl cobertura',
    state: 'Altepetl',
    legislative: 'Tenahuatilli',
    non_legislative: 'Ahmo tenahuatilli',
    total: 'Mochi',
  },
};

function formatNumber(n: number): string {
  return n.toLocaleString('es-MX');
}

export function StateCoverageTable({ states, lang }: StateCoverageTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('state');
  const [sortAsc, setSortAsc] = useState(true);
  const labels = columnLabels[lang];

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

  const totalLeg = states.reduce((s, r) => s + r.legislative, 0);
  const totalNonLeg = states.reduce((s, r) => s + r.non_legislative, 0);
  const totalAll = states.reduce((s, r) => s + r.total, 0);

  const sortTh = (label: string, colKey: SortKey, alignRight = true) => (
    <th
      key={colKey}
      className="py-2 px-3 text-xs font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground transition-colors"
      onClick={() => toggleSort(colKey)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleSort(colKey);
        }
      }}
      tabIndex={0}
      role="columnheader"
      aria-sort={sortKey === colKey ? (sortAsc ? 'ascending' : 'descending') : 'none'}
    >
      <span className={`flex items-center gap-1 ${alignRight ? 'justify-end' : ''}`}>
        {label}
        <ArrowUpDown className="w-3 h-3" />
      </span>
    </th>
  );

  if (states.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <MapIcon className="w-5 h-5 text-muted-foreground" aria-hidden="true" />
          <h2 className="font-semibold text-lg text-foreground">
            {labels.title} ({states.length})
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-muted">
                {sortTh(labels.state, 'state', false)}
                {sortTh(labels.legislative, 'legislative')}
                {sortTh(labels.non_legislative, 'non_legislative')}
                {sortTh(labels.total, 'total')}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.state} className="border-b border-muted/50 hover:bg-muted/30 transition-colors">
                  <td className="py-2 px-3 text-sm text-foreground">{row.state}</td>
                  <td className="py-2 px-3 text-sm text-right tabular-nums text-muted-foreground">
                    {formatNumber(row.legislative)}
                  </td>
                  <td className="py-2 px-3 text-sm text-right tabular-nums text-muted-foreground">
                    {formatNumber(row.non_legislative)}
                  </td>
                  <td className="py-2 px-3 text-sm text-right tabular-nums font-medium text-foreground">
                    {formatNumber(row.total)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-muted font-semibold">
                <td className="py-2 px-3 text-sm">Total</td>
                <td className="py-2 px-3 text-sm text-right tabular-nums">{formatNumber(totalLeg)}</td>
                <td className="py-2 px-3 text-sm text-right tabular-nums">{formatNumber(totalNonLeg)}</td>
                <td className="py-2 px-3 text-sm text-right tabular-nums">{formatNumber(totalAll)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
