'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Calendar, ExternalLink } from 'lucide-react';
import { Badge } from '@tezca/ui';
import { useLang, LOCALE_MAP } from '@/components/providers/LanguageContext';

const content = {
    es: {
        title: 'Historial de Versiones',
        versions: 'versiones publicadas',
        version: 'versión publicada',
        current: 'Vigente',
        superseded: 'Superada',
        published: 'Publicado:',
        effectiveFrom: 'Vigente desde:',
        effectiveUntil: 'Vigente hasta:',
        viewDof: 'Ver en DOF',
        show: 'Mostrar historial',
        hide: 'Ocultar historial',
    },
    en: {
        title: 'Version History',
        versions: 'published versions',
        version: 'published version',
        current: 'Current',
        superseded: 'Superseded',
        published: 'Published:',
        effectiveFrom: 'Effective from:',
        effectiveUntil: 'Effective until:',
        viewDof: 'View in DOF',
        show: 'Show history',
        hide: 'Hide history',
    },
    nah: {
        title: 'Tlanextīlli Ītlācatiliz',
        versions: 'tlanextīlli tlamachiyōtl',
        version: 'tlanextīlli tlamachiyōtl',
        current: 'Āxcān',
        superseded: 'Ōpanōc',
        published: 'Tlanextīlli:',
        effectiveFrom: 'Pēhua:',
        effectiveUntil: 'Tlami:',
        viewDof: 'Xiquitta DOF',
        show: 'Xicnextia tlanextīlli',
        hide: 'Xictlātia tlanextīlli',
    },
};

interface VersionItem {
    publication_date: string | null;
    valid_from?: string;
    valid_to?: string | null;
    dof_url?: string | null;
    change_summary?: string | null;
}

interface VersionTimelineProps {
    versions: VersionItem[];
}

export function VersionTimeline({ versions }: VersionTimelineProps) {
    const { lang } = useLang();
    const t = content[lang];
    const locale = LOCALE_MAP[lang];
    const [expanded, setExpanded] = useState(false);

    if (!versions || versions.length <= 1) {
        return null;
    }

    const formatDate = (dateStr: string | null | undefined) => {
        if (!dateStr) return null;
        return new Date(dateStr).toLocaleDateString(locale, {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    };

    return (
        <section className="mt-8 border rounded-lg bg-card shadow-sm" aria-label={t.title}>
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full p-4 sm:p-6 flex items-center justify-between text-left hover:bg-muted/30 transition-colors rounded-lg"
                aria-expanded={expanded}
            >
                <div className="flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-primary" />
                    <h2 className="text-lg font-bold tracking-tight">{t.title}</h2>
                    <Badge variant="secondary" className="text-xs">
                        {versions.length} {versions.length === 1 ? t.version : t.versions}
                    </Badge>
                </div>
                {expanded ? (
                    <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                    <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
            </button>

            {expanded && (
                <div className="px-4 sm:px-6 pb-4 sm:pb-6">
                    <div className="relative border-l-2 border-primary/20 ml-3 pl-6 space-y-6">
                        {versions.map((version, index) => {
                            const isCurrent = index === 0;
                            // Composite key: publication_date is unique per
                            // version in practice; the index is a tiebreaker
                            // for the rare case where two versions share a date.
                            const versionKey = `${version.publication_date ?? 'unknown'}-${index}`;
                            return (
                                <div key={versionKey} className="relative">
                                    {/* Timeline dot */}
                                    <div
                                        className={`absolute -left-[31px] top-1 w-4 h-4 rounded-full border-2 ${
                                            isCurrent
                                                ? 'bg-primary border-primary'
                                                : 'bg-background border-muted-foreground/40'
                                        }`}
                                    />

                                    <div className={`${isCurrent ? '' : 'opacity-75'}`}>
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-sm font-semibold">
                                                {formatDate(version.publication_date) || 'Fecha desconocida'}
                                            </span>
                                            <Badge
                                                variant={isCurrent ? 'default' : 'outline'}
                                                className="text-xs"
                                            >
                                                {isCurrent ? t.current : t.superseded}
                                            </Badge>
                                        </div>

                                        {version.change_summary && (
                                            <p className="mt-1 text-sm text-muted-foreground">
                                                {version.change_summary}
                                            </p>
                                        )}

                                        <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                                            {version.valid_from && (
                                                <span>{t.effectiveFrom} {formatDate(version.valid_from)}</span>
                                            )}
                                            {version.valid_to && (
                                                <span>{t.effectiveUntil} {formatDate(version.valid_to)}</span>
                                            )}
                                        </div>

                                        {version.dof_url && (
                                            <a
                                                href={version.dof_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline"
                                            >
                                                {t.viewDof}
                                                <ExternalLink className="h-3 w-3" />
                                            </a>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </section>
    );
}
