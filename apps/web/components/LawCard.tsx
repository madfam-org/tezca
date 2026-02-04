'use client';

import { Law } from "@leyesmx/lib";
import { Badge, Card } from "@leyesmx/ui";
import Link from 'next/link';
import { useComparison } from './providers/ComparisonContext';

interface LawCardProps {
    law: Law;
}

export default function LawCard({ law }: LawCardProps) {
    const getGradeVariant = (grade: string = '') => {
        if (grade === 'A') return 'default'; // Greenish usually?
        if (grade === 'C') return 'destructive';
        return 'secondary';
    };

    const { isLawSelected, toggleLaw } = useComparison();
    const isSelected = isLawSelected(law.id);

    // Prevent navigation when clicking the checkbox area
    const handleCheckboxClick = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        toggleLaw(law.id);
    };

    return (
        <Link href={`/laws/${law.id}`}>
            <Card className={`p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 cursor-pointer h-full group relative ${isSelected ? 'border-primary ring-2 ring-primary ring-offset-2' : 'hover:border-crimson-400'}`}>
                <div
                    className="absolute top-4 right-4 z-10 p-2 rounded-full hover:bg-muted/50 transition-colors"
                    onClick={handleCheckboxClick}
                    title="Comparar ley"
                >
                    <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${isSelected ? 'bg-primary border-primary' : 'border-input bg-background'}`}>
                        {isSelected && <span className="text-primary-foreground text-xs">✓</span>}
                    </div>
                </div>

                <h3 className="text-xl font-bold text-crimson-600 dark:text-crimson-400 mb-3 group-hover:text-crimson-700 dark:group-hover:text-crimson-300 transition-colors pr-8">
                    {law.name}
                </h3>

                <div className="flex gap-2 flex-wrap mb-4">
                    <Badge variant={getGradeVariant(law.grade)}>
                        Grade {law.grade}
                    </Badge>
                    <Badge variant="secondary">
                        Prioridad {law.priority}
                    </Badge>
                </div>

                <div className="text-sm text-stone-600 dark:text-stone-400">
                    <span className="font-semibold text-stone-900 dark:text-stone-100">
                        {law.articles?.toLocaleString() ?? 0}
                    </span> artículos •
                    <span className="font-semibold text-forest-600 dark:text-forest-400 ml-1">
                        {law.score}%
                    </span> calidad
                </div>

                {(law.transitorios ?? 0) > 0 && (
                    <div className="text-xs text-stone-500 dark:text-stone-500 mt-2">
                        + {law.transitorios} transitorios
                    </div>
                )}
            </Card>
        </Link>
    );
}

