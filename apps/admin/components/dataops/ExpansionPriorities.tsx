'use client';

import { Card, CardHeader, CardTitle, CardContent } from "@tezca/ui";
import { TrendingUp } from 'lucide-react';
import type { ExpansionPriority } from './types';
import { PriorityRow } from './PriorityRow';

interface ExpansionPrioritiesProps {
  priorities: ExpansionPriority[];
}

export function ExpansionPriorities({ priorities }: ExpansionPrioritiesProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          Prioridades de Expansion
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {priorities.map(p => (
          <PriorityRow key={p.rank} item={p} />
        ))}
      </CardContent>
    </Card>
  );
}
