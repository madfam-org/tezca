'use client';

import { Card, CardHeader, CardTitle, CardContent } from "@tezca/ui";
import { Layers } from 'lucide-react';
import type { TierProgress } from './types';
import { TierProgressBar } from './TierProgressBar';

interface TierProgressListProps {
  tiers: TierProgress[];
}

export function TierProgressList({ tiers }: TierProgressListProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Layers className="w-5 h-5" />
          Progreso por Tier
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {tiers.map(tier => (
          <TierProgressBar key={tier.key} tier={tier} />
        ))}
      </CardContent>
    </Card>
  );
}
