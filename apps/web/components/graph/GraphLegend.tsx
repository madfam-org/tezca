'use client';

import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Leyenda',
        federal: 'Federal',
        state: 'Estatal',
        municipal: 'Municipal',
        size: 'Tamaño = referencias',
        width: 'Grosor = peso',
    },
    en: {
        title: 'Legend',
        federal: 'Federal',
        state: 'State',
        municipal: 'Municipal',
        size: 'Size = references',
        width: 'Width = weight',
    },
    nah: {
        title: 'Tlamachiyotl',
        federal: 'Federal',
        state: 'Altepetl',
        municipal: 'Municipal',
        size: 'Hueyitl = tlanōnotzaliztli',
        width: 'Patlāhuac = etiliztli',
    },
};

const TIER_COLORS = [
    { key: 'federal', color: 'hsl(var(--primary))' },
    { key: 'state', color: 'hsl(var(--chart-2))' },
    { key: 'municipal', color: 'hsl(var(--chart-4))' },
] as const;

export function GraphLegend() {
    const { lang } = useLang();
    const t = content[lang];

    return (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{t.title}:</span>
            {TIER_COLORS.map(({ key, color }) => (
                <span key={key} className="inline-flex items-center gap-1.5">
                    <span
                        className="inline-block w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: color }}
                    />
                    {t[key as keyof typeof t]}
                </span>
            ))}
            <span className="hidden sm:inline">{t.size}</span>
            <span className="hidden sm:inline">{t.width}</span>
        </div>
    );
}
