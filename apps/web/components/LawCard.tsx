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
    const handleCheckboxClick = (e: React.MouseEvent | React.KeyboardEvent) => {
        e.preventDefault();
        e.stopPropagation();
        toggleLaw(law.id);
    };

    const handleCheckboxKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === ' ' || e.key === 'Enter') {
            handleCheckboxClick(e);
        }
    };

    return (
        <Link href={`/laws/${law.id}`}>
            <Card className={`p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 cursor-pointer h-full group relative glass hover:bg-white/40 dark:hover:bg-white/5 border border-white/20 ${isSelected ? 'border-primary ring-2 ring-primary ring-offset-2' : 'hover:border-primary/30'}`}>
                <div
                    className="absolute top-4 right-4 z-10 p-2 rounded-full hover:bg-muted/50 transition-colors"
                    onClick={handleCheckboxClick}
                    onKeyDown={handleCheckboxKeyDown}
                    role="checkbox"
                    aria-checked={isSelected}
                    aria-label="Seleccionar para comparar"
                    tabIndex={0}
                >
                    <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${isSelected ? 'bg-primary border-primary' : 'border-input bg-background/50'}`}>
                        {isSelected && <span className="text-primary-foreground text-xs">✓</span>}
                    </div>
                </div>

                <h3 className="text-xl font-display font-bold text-primary-700 dark:text-primary-300 mb-3 group-hover:text-primary-600 dark:group-hover:text-primary-200 transition-colors pr-8">
                    {law.name}
                </h3>

                <div className="flex gap-2 flex-wrap mb-4">
                    <Badge variant={getGradeVariant(law.grade)} className="shadow-sm">
                        Grade {law.grade}
                    </Badge>
                    <Badge variant="secondary" className="bg-secondary-100 dark:bg-secondary-900/50">
                        Prioridad {law.priority}
                    </Badge>
                </div>

                <div className="text-sm text-neutral-600 dark:text-neutral-400">
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">
                        {law.articles?.toLocaleString() ?? 0}
                    </span> artículos •
                    <span className="font-semibold text-success-500 ml-1">
                        {law.score}%
                    </span> calidad
                </div>

                {(law.transitorios ?? 0) > 0 && (
                    <div className="text-xs text-neutral-500 dark:text-neutral-500 mt-2">
                        + {law.transitorios} transitorios
                    </div>
                )}
            </Card>
        </Link>
    );
}

