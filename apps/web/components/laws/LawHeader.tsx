'use client';

import type { Law, LawVersion } from './types';
import { Badge } from '@tezca/ui';
import { ExternalLink, Calendar, GitCompareArrows, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { useLang, LOCALE_MAP } from '@/components/providers/LanguageContext';
import { BookmarkButton } from '@/components/BookmarkButton';
import { PDFExportButton } from '@/components/PDFExportButton';
import { ExportDropdown } from './ExportDropdown';
import { ShareButtons } from '@/components/ShareButtons';

const content = {
    es: {
        tierState: 'Estatal',
        tierFederal: 'Federal',
        published: 'Publicado:',
        viewOriginal: 'Ver documento original',
        compare: 'Comparar',
        abrogada: 'Esta ley puede estar abrogada',
        derogada: 'Esta ley puede estar derogada',
        lastVerified: 'Verificado:',
    },
    en: {
        tierState: 'State',
        tierFederal: 'Federal',
        published: 'Published:',
        viewOriginal: 'View original document',
        compare: 'Compare',
        abrogada: 'This law may be repealed',
        derogada: 'This law may be abrogated',
        lastVerified: 'Verified:',
    },
    nah: {
        tierState: 'Altepetl',
        tierFederal: 'Federal',
        published: 'Tlanextīlli:',
        viewOriginal: 'Xiquitta achto āmatl',
        compare: 'Tlanānamiquiliztli',
        abrogada: 'Inīn tenahuatilli huelīz ōmopōuh',
        derogada: 'Inīn tenahuatilli huelīz ōmocuep',
        lastVerified: 'Tlaneltilīlli:',
    },
};

interface LawHeaderProps {
    law: Law;
    version: LawVersion;
}

export function LawHeader({ law, version }: LawHeaderProps) {
    const { lang } = useLang();
    const t = content[lang];
    const locale = LOCALE_MAP[lang];

    return (
        <header className="border-b bg-card">
            <div className="container mx-auto px-4 py-6 sm:py-8">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
                    <div className="flex-1 space-y-4">
                        <div className="flex flex-wrap items-center gap-2">
                            <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
                                {law.category}
                            </Badge>
                            <Badge variant="outline" className="text-muted-foreground border-muted-foreground/20">
                                {law.tier === 'state' ? t.tierState : t.tierFederal}
                            </Badge>
                            {law.state && (
                                <Badge variant="outline" className="text-muted-foreground border-muted-foreground/20">
                                    {law.state}
                                </Badge>
                            )}
                        </div>

                        <h1 className="text-xl sm:text-3xl md:text-4xl font-bold tracking-tight text-foreground">
                            {law.name}
                        </h1>

                        {version.publication_date && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <Calendar className="h-4 w-4" />
                                <span>
                                    {t.published} {new Date(version.publication_date).toLocaleDateString(locale, {
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric'
                                    })}
                                </span>
                            </div>
                        )}

                        {law.status && law.status !== 'vigente' && law.status !== 'unknown' && (
                            <div className="flex items-center gap-2 rounded-md bg-warning-50 dark:bg-warning-500/10 px-3 py-2 text-sm text-warning-700 dark:text-warning-500">
                                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                                <span>{law.status === 'abrogada' ? t.abrogada : t.derogada}</span>
                            </div>
                        )}

                        {law.last_verified && (
                            <div className="text-xs text-muted-foreground">
                                {t.lastVerified} {new Date(law.last_verified).toLocaleDateString(locale)}
                            </div>
                        )}
                    </div>


                    <div className="flex flex-wrap gap-2">
                        <BookmarkButton lawId={law.official_id || ''} lawName={law.name} />
                        <ExportDropdown lawId={law.official_id || ''} />
                        <PDFExportButton />
                        <Link
                            href={`/compare?laws=${encodeURIComponent(law.official_id || '')}`}
                            className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                        >
                            <GitCompareArrows className="h-4 w-4" />
                            <span className="hidden sm:inline">{t.compare}</span>
                        </Link>

                        {version.xml_file && (
                            <a
                                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/media/xml/${version.xml_file}`}
                                download
                                className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
                            >
                                <span className="font-bold">XML</span>
                                <span className="hidden sm:inline">Akoma Ntoso</span>
                            </a>
                        )}

                        {version.dof_url && (
                            <a
                                href={version.dof_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 rounded-md bg-secondary px-4 py-2 text-sm font-medium text-secondary-foreground transition-colors hover:bg-secondary/80"
                            >
                                {t.viewOriginal}
                                <ExternalLink className="h-4 w-4" />
                            </a>
                        )}
                    </div>
                </div>

                <div className="mt-4 pt-4 border-t border-border/50">
                    <ShareButtons title={law.name} />
                </div>
            </div>
        </header>
    );
}
