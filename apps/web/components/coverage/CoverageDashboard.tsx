'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@tezca/ui';
import { api } from '@/lib/api';

type Lang = 'es' | 'en' | 'nah';

interface CoverageTier {
  id: string;
  name: Record<string, string>;
  have: number;
  universe: number | null;
  pct: number | null;
  color: string;
  note?: Record<string, string>;
}

interface CoverageData {
  total_laws: number;
  total_items: number;
  total_universe: number;
  overall_pct: number;
  tiers: CoverageTier[];
  last_updated: string;
}

const labels = {
  es: {
    loading: 'Cargando estadísticas...',
    error: 'No se pudieron cargar las estadísticas',
    overall: 'Cobertura general',
    captured: 'Capturados',
    universe: 'Universo conocido',
    coverage: 'Cobertura',
    dbLaws: 'Leyes en base de datos',
    unknown: 'Desconocido',
    na: 'N/D',
  },
  en: {
    loading: 'Loading statistics...',
    error: 'Could not load statistics',
    overall: 'Overall coverage',
    captured: 'Captured',
    universe: 'Known universe',
    coverage: 'Coverage',
    dbLaws: 'Laws in database',
    unknown: 'Unknown',
    na: 'N/A',
  },
  nah: {
    loading: 'Motēmoa tlapohualli...',
    error: 'Ahmo huelīz motēmoa',
    overall: 'Mochi cobertura',
    captured: 'Mopiya',
    universe: 'Cemānāhuac',
    coverage: 'Cobertura',
    dbLaws: 'Tenahuatilli āmoxcalli',
    unknown: 'Ahmo machiz',
    na: 'N/D',
  },
};

function formatNumber(n: number): string {
  return n.toLocaleString('es-MX');
}

function ProgressBar({ pct, color }: { pct: number | null; color: string }) {
  if (pct === null) return <div className="h-3 w-full rounded-full bg-muted" />;

  const bgClass =
    color === 'green'
      ? 'bg-emerald-500'
      : color === 'yellow'
        ? 'bg-amber-500'
        : 'bg-red-500';

  return (
    <div className="h-3 w-full rounded-full bg-muted overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${bgClass}`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

export function CoverageDashboard({ lang }: { lang: Lang }) {
  const [data, setData] = useState<CoverageData | null>(null);
  const [error, setError] = useState(false);
  const t = labels[lang];

  useEffect(() => {
    api.getCoverage()
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div className="p-4 rounded-md bg-destructive/10 text-destructive text-sm">
        {t.error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-muted-foreground text-sm animate-pulse py-8 text-center">
        {t.loading}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Overall summary */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
            <div>
              <h2 className="font-semibold text-lg text-foreground">{t.overall}</h2>
              <p className="text-sm text-muted-foreground">
                {t.dbLaws}: {formatNumber(data.total_laws)}
              </p>
            </div>
            <div className="text-right">
              <span className="text-3xl font-bold text-foreground">
                {data.overall_pct}%
              </span>
              <p className="text-xs text-muted-foreground">
                {formatNumber(data.total_items)} / {formatNumber(data.total_universe)}
              </p>
            </div>
          </div>
          <ProgressBar
            pct={data.overall_pct}
            color={data.overall_pct > 90 ? 'green' : data.overall_pct > 50 ? 'yellow' : 'red'}
          />
        </CardContent>
      </Card>

      {/* Per-tier cards */}
      <div className="space-y-3">
        {data.tiers.map((tier) => (
          <Card key={tier.id}>
            <CardContent className="p-4">
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                {/* Name and counts */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm text-foreground truncate">
                    {tier.name[lang] || tier.name.es}
                  </h3>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span>
                      {t.captured}: <span className="font-medium text-foreground">{formatNumber(tier.have)}</span>
                    </span>
                    <span>
                      {t.universe}:{' '}
                      <span className="font-medium text-foreground">
                        {tier.universe !== null ? formatNumber(tier.universe) : t.unknown}
                      </span>
                    </span>
                  </div>
                </div>

                {/* Percentage */}
                <div className="text-right shrink-0 w-16">
                  <span className="text-lg font-bold text-foreground">
                    {tier.pct !== null ? `${tier.pct}%` : t.na}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-3">
                <ProgressBar pct={tier.pct} color={tier.color} />
              </div>

              {/* Note */}
              {tier.note && (
                <p className="mt-2 text-xs text-muted-foreground italic">
                  {tier.note[lang] || tier.note.es}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Last updated */}
      {data.last_updated && (
        <p className="text-xs text-muted-foreground text-center">
          {lang === 'en' ? 'Last updated' : lang === 'nah' ? 'Tlayancuīc' : 'Última actualización'}: {data.last_updated}
        </p>
      )}
    </div>
  );
}
