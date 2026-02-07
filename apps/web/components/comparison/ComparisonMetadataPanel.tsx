'use client';

import { Badge } from "@tezca/ui";
import type { ComparisonLawData } from './types';
import { useLang } from '@/components/providers/LanguageContext';
import type { Lang } from '@/components/providers/LanguageContext';

const tierLabels: Record<Lang, Record<string, string>> = {
    es: { federal: 'Federal', state: 'Estatal', municipal: 'Municipal', unknown: 'Desconocido' },
    en: { federal: 'Federal', state: 'State', municipal: 'Municipal', unknown: 'Unknown' },
};

const content = {
    es: {
        articlesInCommon: (n: number) => n === 1 ? 'artículo en común' : 'artículos en común',
        articles: 'artículos',
    },
    en: {
        articlesInCommon: (n: number) => n === 1 ? 'article in common' : 'articles in common',
        articles: 'articles',
    },
};

function getTierLabel(tier: number | string | undefined, lang: Lang): string {
    const labels = tierLabels[lang];
    if (tier === 'federal' || tier === 1) return labels.federal;
    if (tier === 'state' || tier === 2) return labels.state;
    if (tier === 'municipal' || tier === 3) return labels.municipal;
    return labels.unknown;
}

function tierVariant(tier: number | string | undefined): 'default' | 'secondary' | 'outline' {
    if (tier === 'federal' || tier === 1) return 'default';
    if (tier === 'state' || tier === 2) return 'secondary';
    return 'outline';
}

interface ComparisonMetadataPanelProps {
    laws: ComparisonLawData[];
    matchCount: number;
}

export function ComparisonMetadataPanel({ laws, matchCount }: ComparisonMetadataPanelProps) {
    const { lang } = useLang();
    const t = content[lang];

    if (laws.length < 2) return null;

    return (
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 sm:gap-4 px-4 sm:px-6 py-3 sm:py-4 border-b bg-muted/20">
            {/* Law A */}
            <MetadataCard law={laws[0]} lang={lang} articlesLabel={t.articles} />

            {/* Center stats */}
            <div className="hidden sm:flex flex-col items-center justify-center px-4 text-center">
                <span className="text-2xl font-bold text-primary">{matchCount}</span>
                <span className="text-xs text-muted-foreground">
                    {t.articlesInCommon(matchCount)}
                </span>
            </div>

            {/* Law B */}
            <MetadataCard law={laws[1]} lang={lang} articlesLabel={t.articles} />

            {/* Mobile center stats */}
            <div className="sm:hidden text-center py-2 border-t">
                <span className="text-lg font-bold text-primary">{matchCount}</span>
                <span className="text-xs text-muted-foreground ml-1">
                    {t.articlesInCommon(matchCount)}
                </span>
            </div>
        </div>
    );
}

function MetadataCard({ law, lang, articlesLabel }: { law: ComparisonLawData; lang: Lang; articlesLabel: string }) {
    return (
        <div className="rounded-lg border bg-card p-3 space-y-1.5">
            <h3 className="text-sm font-semibold truncate" title={law.meta.name}>
                {law.meta.name}
            </h3>
            <div className="flex flex-wrap gap-1.5">
                <Badge variant={tierVariant(law.meta.tier)}>
                    {getTierLabel(law.meta.tier, lang)}
                </Badge>
                {law.meta.category && (
                    <Badge variant="outline" className="text-xs">
                        {law.meta.category}
                    </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                    {law.details.total} {articlesLabel}
                </Badge>
            </div>
        </div>
    );
}
