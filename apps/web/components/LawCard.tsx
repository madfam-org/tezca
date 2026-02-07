'use client';

import { Law } from "@tezca/lib";
import { Badge, Card } from "@tezca/ui";
import Link from 'next/link';
import { useComparison } from './providers/ComparisonContext';
import { useLang } from '@/components/providers/LanguageContext';
import { ComparisonHint } from '@/components/ComparisonHint';

const content = {
    es: {
        selectCompare: 'Seleccionar para comparar',
        grade: 'Grado',
        priority: 'Prioridad',
        articles: 'artículos',
        quality: 'calidad',
        transitory: 'transitorios',
    },
    en: {
        selectCompare: 'Select to compare',
        grade: 'Grade',
        priority: 'Priority',
        articles: 'articles',
        quality: 'quality',
        transitory: 'transitory',
    },
    nah: {
        selectCompare: 'Xicpēpena ic tlanānamiquiliztli',
        grade: 'Tlachiyaliztli',
        priority: 'Tlaiyōcāyōtl',
        articles: 'tlanahuatilli',
        quality: 'cuallōtl',
        transitory: 'tlanquiliztli',
    },
};

interface LawCardProps {
    law: Law;
}

export default function LawCard({ law }: LawCardProps) {
    const { lang } = useLang();
    const t = content[lang];

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
        <Link href={`/leyes/${law.id}`}>
            <Card className={`p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 cursor-pointer h-full group relative glass hover:bg-white/40 dark:hover:bg-white/5 border border-white/20 ${isSelected ? 'border-primary ring-2 ring-primary ring-offset-2' : 'hover:border-primary/30'}`}>
                <div
                    className="absolute top-4 right-4 z-10 p-3 rounded-full hover:bg-muted/50 transition-colors"
                    onClick={handleCheckboxClick}
                    onKeyDown={handleCheckboxKeyDown}
                    role="checkbox"
                    aria-checked={isSelected}
                    aria-label={t.selectCompare}
                    tabIndex={0}
                >
                    <ComparisonHint />
                    <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${isSelected ? 'bg-primary border-primary' : 'border-input bg-background/50'}`}>
                        {isSelected && <span className="text-primary-foreground text-xs">✓</span>}
                    </div>
                </div>

                <h3 className="text-xl font-display font-bold text-primary-700 dark:text-primary-300 mb-3 group-hover:text-primary-600 dark:group-hover:text-primary-200 transition-colors pr-8">
                    {law.name}
                </h3>

                <div className="flex gap-2 flex-wrap mb-4">
                    <Badge variant={getGradeVariant(law.grade)} className="shadow-sm">
                        {t.grade} {law.grade}
                    </Badge>
                    <Badge variant="secondary" className="bg-secondary-100 dark:bg-secondary-900/50">
                        {t.priority} {law.priority}
                    </Badge>
                </div>

                <div className="text-sm text-neutral-600 dark:text-neutral-400">
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">
                        {law.articles?.toLocaleString() ?? 0}
                    </span> {t.articles} •
                    <span className="font-semibold text-success-500 ml-1">
                        {law.score}%
                    </span> {t.quality}
                </div>

                {(law.transitorios ?? 0) > 0 && (
                    <div className="text-xs text-neutral-500 dark:text-neutral-500 mt-2">
                        + {law.transitorios} {t.transitory}
                    </div>
                )}
            </Card>
        </Link>
    );
}
