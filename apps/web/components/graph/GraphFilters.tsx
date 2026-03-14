'use client';

import { useLang } from '@/components/providers/LanguageContext';
import { CATEGORY_COLORS, CATEGORY_LABELS, DEFAULT_COLOR } from './graphConstants';

const content = {
    es: { categories: 'Categorías', all: 'Todas' },
    en: { categories: 'Categories', all: 'All' },
    nah: { categories: 'Tlamantli', all: 'Mochīntin' },
};

interface GraphFiltersProps {
    categories: string[];
    hiddenCategories: Set<string>;
    onToggleCategory: (cat: string) => void;
    onShowAll: () => void;
    floating?: boolean;
}

export function GraphFilters({
    categories,
    hiddenCategories,
    onToggleCategory,
    onShowAll,
    floating,
}: GraphFiltersProps) {
    const { lang } = useLang();
    const t = content[lang];

    const wrapperClass = floating
        ? 'absolute top-3 left-3 z-10 rounded-lg border bg-card/90 backdrop-blur-sm p-2 shadow-md'
        : '';

    return (
        <div className={wrapperClass}>
            <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-medium text-muted-foreground mr-1">{t.categories}:</span>
                <button
                    onClick={onShowAll}
                    className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                        hiddenCategories.size === 0
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                >
                    {t.all}
                </button>
                {categories.map((cat) => {
                    const isHidden = hiddenCategories.has(cat);
                    const color = CATEGORY_COLORS[cat] ?? DEFAULT_COLOR;
                    const label = CATEGORY_LABELS[cat]?.[lang] ?? cat;
                    return (
                        <button
                            key={cat}
                            onClick={() => onToggleCategory(cat)}
                            className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full transition-all ${
                                isHidden
                                    ? 'bg-muted/50 text-muted-foreground/50'
                                    : 'bg-muted text-foreground'
                            }`}
                        >
                            <span
                                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                                style={{ backgroundColor: color, opacity: isHidden ? 0.3 : 1 }}
                            />
                            {label}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
