'use client';

import { useState } from 'react';
import { Badge, Button, Card, CardContent } from '@tezca/ui';

type Lang = 'es' | 'en' | 'nah';

interface CoverageView {
  label: Record<string, string>;
  universe: number;
  captured: number;
  pct: number | null;
}

interface CoverageViewTabsProps {
  views: Record<string, CoverageView>;
  lang: Lang;
}

const VIEW_ORDER = [
  'leyes_vigentes',
  'marco_juridico_completo',
  'normatividad_primaria',
  'marco_juridico_total',
];

const sectionTitle: Record<Lang, string> = {
  es: 'Perspectivas de cobertura',
  en: 'Coverage perspectives',
  nah: 'Cobertura tlanextiliztli',
};

function formatNumber(n: number): string {
  return n.toLocaleString('es-MX');
}

function ProgressBar({ pct }: { pct: number | null }) {
  if (pct === null) return <div className="h-3 w-full rounded-full bg-muted" />;

  const bgClass =
    pct >= 90 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="h-3 w-full rounded-full bg-muted overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${bgClass}`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

export function CoverageViewTabs({ views, lang }: CoverageViewTabsProps) {
  const viewKeys = VIEW_ORDER.filter((k) => k in views);
  const [active, setActive] = useState(viewKeys[0] ?? '');

  if (viewKeys.length === 0) return null;

  const activeView = views[active];

  return (
    <div className="space-y-4">
      <h2 className="font-semibold text-lg text-foreground">{sectionTitle[lang]}</h2>

      {/* Tab buttons */}
      <div className="flex flex-wrap gap-2" role="tablist">
        {viewKeys.map((key) => {
          const view = views[key];
          const isActive = key === active;
          return (
            <Button
              key={key}
              role="tab"
              aria-selected={isActive}
              variant={isActive ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActive(key)}
              className="gap-2"
            >
              {view.label[lang] || view.label.es}
              {view.pct !== null && (
                <Badge variant="secondary" className="text-xs px-1.5 py-0">
                  {view.pct}%
                </Badge>
              )}
            </Button>
          );
        })}
      </div>

      {/* Active view detail */}
      {activeView && (
        <Card>
          <CardContent className="p-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
              <div>
                <h3 className="font-medium text-foreground">
                  {activeView.label[lang] || activeView.label.es}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {formatNumber(activeView.captured)} / {formatNumber(activeView.universe)}
                </p>
              </div>
              <span className="text-2xl font-bold text-foreground">
                {activeView.pct !== null ? `${activeView.pct}%` : 'N/D'}
              </span>
            </div>
            <ProgressBar pct={activeView.pct} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
