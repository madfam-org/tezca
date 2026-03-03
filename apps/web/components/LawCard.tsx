'use client';

import type { Law, LawListItem } from "@tezca/lib";
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
        federal: 'Federal',
        state: 'Estatal',
        municipal: 'Municipal',
        versions: 'versiones',
    },
    en: {
        selectCompare: 'Select to compare',
        grade: 'Grade',
        priority: 'Priority',
        articles: 'articles',
        quality: 'quality',
        transitory: 'transitory',
        federal: 'Federal',
        state: 'State',
        municipal: 'Municipal',
        versions: 'versions',
    },
    nah: {
        selectCompare: 'Xicpēpena ic tlanānamiquiliztli',
        grade: 'Tlachiyaliztli',
        priority: 'Tlaiyōcāyōtl',
        articles: 'tlanahuatilli',
        quality: 'cuallōtl',
        transitory: 'tlanquiliztli',
        federal: 'Hueyaltepetl',
        state: 'Altepetl',
        municipal: 'Calpulli',
        versions: 'tlamantli',
    },
};

const tierVariantMap: Record<string, 'default' | 'secondary' | 'outline'> = {
    federal: 'default',
    state: 'secondary',
    municipal: 'outline',
};

interface LawCardProps {
    law: Law | LawListItem;
}

export default function LawCard({ law }: LawCardProps) {
    const { lang } = useLang();
    const t = content[lang];

    const getGradeVariant = (grade: string = '') => {
        if (grade === 'A') return 'default';
        if (grade === 'C') return 'destructive';
        return 'secondary';
    };

    const { isLawSelected, toggleLaw } = useComparison();
    const isSelected = isLawSelected(law.id);

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

    // Check if this is a full Law (with grade/score) or a LawListItem
    const hasDetailFields = 'grade' in law && law.grade != null;
    const tierLabel = law.tier ? (t as Record<string, string>)[law.tier] ?? law.tier : null;

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

                <h3 className="text-xl font-display font-bold text-foreground mb-3 group-hover:text-primary transition-colors pr-8">
                    {law.name}
                </h3>

                <div className="flex gap-2 flex-wrap mb-4">
                    {hasDetailFields ? (
                        <>
                            <Badge variant={getGradeVariant((law as Law).grade)} className="shadow-sm">
                                {t.grade} {(law as Law).grade}
                            </Badge>
                            {(law as Law).priority != null && (
                                <Badge variant="secondary">
                                    {t.priority} {(law as Law).priority}
                                </Badge>
                            )}
                        </>
                    ) : (
                        <>
                            {tierLabel && (
                                <Badge variant={tierVariantMap[law.tier!] ?? 'outline'}>
                                    {tierLabel}
                                </Badge>
                            )}
                            {law.category && (
                                <Badge variant="outline" className="capitalize">
                                    {law.category}
                                </Badge>
                            )}
                            {law.law_type && (
                                <Badge variant="outline" className="capitalize">
                                    {law.law_type.replace(/_/g, ' ')}
                                </Badge>
                            )}
                        </>
                    )}
                </div>

                {hasDetailFields && (
                    <div className="text-sm text-muted-foreground">
                        <span className="font-semibold text-foreground">
                            {(law as Law).articles?.toLocaleString() ?? 0}
                        </span> {t.articles} •
                        <span className="font-semibold text-foreground ml-1">
                            {(law as Law).score}%
                        </span> {t.quality}
                    </div>
                )}

                {!hasDetailFields && typeof (law as LawListItem).versions === 'number' && (law as LawListItem).versions > 0 && (
                    <p className="text-sm text-muted-foreground">
                        {(law as LawListItem).versions} {t.versions}
                    </p>
                )}

                {hasDetailFields && ((law as Law).transitorios ?? 0) > 0 && (
                    <div className="text-xs text-muted-foreground mt-2">
                        + {(law as Law).transitorios} {t.transitory}
                    </div>
                )}
            </Card>
        </Link>
    );
}
