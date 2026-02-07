'use client';

import { RefreshCw, Database, TrendingUp } from 'lucide-react';
import { Button } from "@tezca/ui";
import type { DashboardData } from './types';

interface CoverageHeaderProps {
  data: DashboardData | null;
  loading: boolean;
  onRefresh: () => void;
}

export function CoverageHeader({ data, loading, onRefresh }: CoverageHeaderProps) {
  const totalInDb = data?.tier_progress.reduce((sum, t) => sum + t.in_db, 0) ?? 0;
  const totalScraped = data?.tier_progress.reduce((sum, t) => sum + t.scraped, 0) ?? 0;
  const totalGaps = data?.gap_summary.total ?? 0;

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Database className="w-8 h-8" />
          Coverage Dashboard
        </h1>
        {data && (
          <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              {totalInDb.toLocaleString()} en BD
            </span>
            <span>{totalScraped.toLocaleString()} scrapeados</span>
            <span>{totalGaps} brechas</span>
          </div>
        )}
      </div>
      <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
        <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
        Actualizar
      </Button>
    </div>
  );
}
