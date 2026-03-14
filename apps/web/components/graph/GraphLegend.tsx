'use client';

import { useLang } from '@/components/providers/LanguageContext';
import {
    type ColorMode,
    CATEGORY_COLORS,
    TIER_COLORS,
    CATEGORY_LABELS,
    TIER_LABELS,
    DEFAULT_COLOR,
} from './graphConstants';

const content = {
    es: {
        colorBy: 'Color por',
        category: 'Categoría',
        tier: 'Nivel',
        size: 'Tamaño = referencias',
        width: 'Grosor = peso',
    },
    en: {
        colorBy: 'Color by',
        category: 'Category',
        tier: 'Tier',
        size: 'Size = references',
        width: 'Width = weight',
    },
    nah: {
        colorBy: 'Tlapalli īpan',
        category: 'Tlamantli',
        tier: 'Tlamamatl',
        size: 'Hueyitl = tlanōnotzaliztli',
        width: 'Patlāhuac = etiliztli',
    },
};

interface GraphLegendProps {
    colorMode: ColorMode;
    onColorModeChange: (mode: ColorMode) => void;
    hiddenCategories?: Set<string>;
    onToggleCategory?: (cat: string) => void;
    categories?: string[];
    floating?: boolean;
}

export function GraphLegend({
    colorMode,
    onColorModeChange,
    hiddenCategories,
    onToggleCategory,
    categories,
    floating,
}: GraphLegendProps) {
    const { lang } = useLang();
    const t = content[lang];

    const wrapperClass = floating
        ? 'absolute bottom-3 left-3 z-10 rounded-lg border bg-card/90 backdrop-blur-sm p-3 shadow-md max-w-xs'
        : 'flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground';

    return (
        <div className={wrapperClass}>
            {/* Color mode toggle */}
            <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-medium text-foreground">{t.colorBy}:</span>
                <button
                    onClick={() => onColorModeChange('category')}
                    className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                        colorMode === 'category'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                >
                    {t.category}
                </button>
                <button
                    onClick={() => onColorModeChange('tier')}
                    className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                        colorMode === 'tier'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    }`}
                >
                    {t.tier}
                </button>
            </div>

            {/* Legend items */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                {colorMode === 'category' ? (
                    (categories ?? Object.keys(CATEGORY_COLORS)).map((cat) => {
                        // Deduplicate synonym keys
                        if (cat === 'constitutional' && categories?.includes('constitucional')) return null;
                        const isHidden = hiddenCategories?.has(cat);
                        const color = CATEGORY_COLORS[cat] ?? DEFAULT_COLOR;
                        const label = CATEGORY_LABELS[cat]?.[lang] ?? cat;
                        return (
                            <button
                                key={cat}
                                onClick={() => onToggleCategory?.(cat)}
                                className={`inline-flex items-center gap-1 transition-opacity ${
                                    isHidden ? 'opacity-30' : 'opacity-100'
                                } ${onToggleCategory ? 'cursor-pointer hover:opacity-70' : 'cursor-default'}`}
                            >
                                <span
                                    className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: color }}
                                />
                                {label}
                            </button>
                        );
                    })
                ) : (
                    Object.entries(TIER_COLORS).map(([key, color]) => (
                        <span key={key} className="inline-flex items-center gap-1">
                            <span
                                className="inline-block w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: color }}
                            />
                            {TIER_LABELS[key]?.[lang] ?? key}
                        </span>
                    ))
                )}
                <span className="hidden sm:inline">{t.size}</span>
                <span className="hidden sm:inline">{t.width}</span>
            </div>
        </div>
    );
}
