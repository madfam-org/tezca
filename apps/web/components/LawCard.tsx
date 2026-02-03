'use client';

import { Law } from '@/lib/laws';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import Link from 'next/link';

interface LawCardProps {
    law: Law;
}

export default function LawCard({ law }: LawCardProps) {
    const gradeColors = {
        A: 'success' as const,
        B: 'warning' as const,
        C: 'error' as const
    };

    return (
        <Link href={`/laws/${law.id}`}>
            <Card className="p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 hover:border-crimson-400 cursor-pointer h-full group">
                <h3 className="text-xl font-bold text-crimson-600 dark:text-crimson-400 mb-3 group-hover:text-crimson-700 dark:group-hover:text-crimson-300 transition-colors">
                    {law.name}
                </h3>

                <div className="flex gap-2 flex-wrap mb-4">
                    <Badge variant={gradeColors[law.grade]}>
                        Grade {law.grade}
                    </Badge>
                    <Badge variant="secondary">
                        Prioridad {law.priority}
                    </Badge>
                </div>

                <div className="text-sm text-stone-600 dark:text-stone-400">
                    <span className="font-semibold text-stone-900 dark:text-stone-100">
                        {law.articles.toLocaleString()}
                    </span> artículos •
                    <span className="font-semibold text-forest-600 dark:text-forest-400 ml-1">
                        {law.score}%
                    </span> calidad
                </div>

                {law.transitorios > 0 && (
                    <div className="text-xs text-stone-500 dark:text-stone-500 mt-2">
                        + {law.transitorios} transitorios
                    </div>
                )}
            </Card>
        </Link>
    );
}

