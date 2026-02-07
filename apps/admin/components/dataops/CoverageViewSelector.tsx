'use client';

import { Button, Badge } from "@tezca/ui";
import type { CoverageView } from './types';

interface CoverageViewSelectorProps {
  views: Record<string, CoverageView>;
  activeView: string;
  onSelect: (key: string) => void;
}

const VIEW_ORDER = ['leyes_vigentes', 'marco_juridico_completo', 'normatividad_primaria', 'marco_juridico_total'];

export function CoverageViewSelector({ views, activeView, onSelect }: CoverageViewSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {VIEW_ORDER.map(key => {
        const view = views[key];
        if (!view) return null;
        const isActive = key === activeView;
        return (
          <Button
            key={key}
            variant={isActive ? 'default' : 'outline'}
            size="sm"
            onClick={() => onSelect(key)}
            className="text-xs"
          >
            {view.label}
            <Badge variant="secondary" className="ml-2 text-xs">
              {view.pct}%
            </Badge>
          </Button>
        );
      })}
    </div>
  );
}
