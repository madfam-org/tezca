
'use client';

import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { Button } from "@tezca/ui";
import Link from 'next/link';
import { ArrowLeft, Loader2, Map as MapIcon } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ComparisonPane } from './comparison/ComparisonPane';
import { ComparisonMetadataPanel } from './comparison/ComparisonMetadataPanel';
import { ComparisonToolbar } from './comparison/ComparisonToolbar';
import type { ComparisonLawData } from './comparison/types';
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        loadError: 'No se pudieron cargar las leyes.',
        analyzing: 'Analizando estructura legal...',
        comparing: (n: number) => `Comparando ${n} documentos`,
        selectTitle: 'Selecciona leyes para comparar',
        selectDesc: 'Necesitas al menos dos leyes para usar la herramienta de comparación inteligente.',
        goToSearch: 'Ir al Buscador',
        backFull: 'Volver',
        backShort: 'Atrás',
        titleFull: 'Comparación Estructural',
        titleShort: 'Comparación',
    },
    en: {
        loadError: 'Could not load the laws.',
        analyzing: 'Analyzing legal structure...',
        comparing: (n: number) => `Comparing ${n} documents`,
        selectTitle: 'Select laws to compare',
        selectDesc: 'You need at least two laws to use the intelligent comparison tool.',
        goToSearch: 'Go to Search',
        backFull: 'Back',
        backShort: 'Back',
        titleFull: 'Structural Comparison',
        titleShort: 'Compare',
    },
    nah: {
        loadError: 'Ahmo huelītic in tenahuatilli.',
        analyzing: 'Tlanānamiquiliztli tenahuatilli tlachiyaliztli...',
        comparing: (n: number) => `Tlanānamiquiliztli ${n} āmatl`,
        selectTitle: 'Xicpēpena tenahuatilli ic tlanānamiquiliztli',
        selectDesc: 'Monequi ōmē tenahuatilli ic tlanānamiquiliztli.',
        goToSearch: 'Tlatemoliztli',
        backFull: 'Xicmocuepa',
        backShort: 'Mocuepa',
        titleFull: 'Tlanānamiquiliztli Tenahuatilli',
        titleShort: 'Tlanānamiquiliztli',
    },
};

interface ComparisonViewProps {
    lawIds: string[];
}

export default function ComparisonView({ lawIds }: ComparisonViewProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [data, setData] = useState<ComparisonLawData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [syncScroll, setSyncScroll] = useState(false);

    const scrollRefA = useRef<HTMLDivElement | null>(null);
    const scrollRefB = useRef<HTMLDivElement | null>(null);
    const isSyncing = useRef(false);

    useEffect(() => {
        async function fetchData() {
            if (lawIds.length < 2) {
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                const promises = lawIds.map(async (id) => {
                    const [meta, articles, structureData] = await Promise.all([
                        api.getLaw(id),
                        api.getLawArticles(id),
                        api.getLawStructure(id),
                    ]);
                    return {
                        meta,
                        details: articles,
                        structure: structureData?.structure ?? [],
                    } satisfies ComparisonLawData;
                });

                const results = await Promise.all(promises);
                setData(results);
            } catch (err) {
                console.error("Comparison fetch error", err);
                setError(t.loadError);
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, [lawIds, t.loadError]);

    // Article matching: intersection of article IDs across both laws
    const matchedIds = useMemo(() => {
        if (data.length < 2) return new Set<string>();
        const idsA = new Set(data[0].details.articles.map(a => a.article_id));
        const idsB = new Set(data[1].details.articles.map(a => a.article_id));
        const intersection = new Set<string>();
        for (const id of idsA) {
            if (idsB.has(id)) intersection.add(id);
        }
        return intersection;
    }, [data]);

    // Build article text maps for diff highlighting
    const articleMaps = useMemo((): [Map<string, string>, Map<string, string>] => {
        if (data.length < 2) {
            const empty = new Map() as Map<string, string>;
            return [empty, new Map() as Map<string, string>];
        }
        const mapA = new Map() as Map<string, string>;
        const mapB = new Map() as Map<string, string>;
        for (const a of data[0].details.articles) mapA.set(a.article_id, a.text);
        for (const a of data[1].details.articles) mapB.set(a.article_id, a.text);
        return [mapA, mapB];
    }, [data]);

    // Synced scroll handler using scroll ratio
    const handleScroll = useCallback((source: 'a' | 'b') => {
        if (!syncScroll || isSyncing.current) return;
        isSyncing.current = true;

        requestAnimationFrame(() => {
            const srcEl = source === 'a' ? scrollRefA.current : scrollRefB.current;
            const tgtEl = source === 'a' ? scrollRefB.current : scrollRefA.current;

            if (srcEl && tgtEl) {
                const maxScroll = srcEl.scrollHeight - srcEl.clientHeight;
                const ratio = maxScroll > 0 ? srcEl.scrollTop / maxScroll : 0;
                const targetMax = tgtEl.scrollHeight - tgtEl.clientHeight;
                tgtEl.scrollTop = ratio * targetMax;
            }

            isSyncing.current = false;
        });
    }, [syncScroll]);

    if (loading) {
        return (
            <div className="flex h-[80vh] items-center justify-center flex-col px-4" aria-live="polite">
                <Loader2 className="h-8 w-8 sm:h-10 sm:w-10 animate-spin text-primary mb-4" />
                <h2 className="text-lg sm:text-xl font-medium text-center">{t.analyzing}</h2>
                <p className="text-muted-foreground text-xs sm:text-sm mt-2 text-center">{t.comparing(lawIds.length)}</p>
            </div>
        );
    }

    if (error) return <div role="alert" className="text-destructive text-center p-6 sm:p-10 text-sm sm:text-base">{error}</div>;

    if (lawIds.length < 2) {
        return (
            <div className="flex flex-col items-center justify-center py-12 sm:py-20 px-4">
                <h2 className="text-xl sm:text-2xl font-bold mb-4 text-center">{t.selectTitle}</h2>
                <p className="text-sm sm:text-base text-muted-foreground mb-6 max-w-md text-center">
                    {t.selectDesc}
                </p>
                <Button asChild>
                    <Link href="/busqueda">{t.goToSearch}</Link>
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100dvh-80px)]">
            {/* Header */}
            <div className="flex items-center gap-2 sm:gap-4 py-3 sm:py-4 px-4 sm:px-6 border-b">
                <Button asChild variant="ghost" size="sm">
                    <Link href="/busqueda">
                        <ArrowLeft className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                        <span className="hidden sm:inline">{t.backFull}</span>
                        <span className="sm:hidden text-xs">{t.backShort}</span>
                    </Link>
                </Button>
                <div>
                    <h1 className="text-base sm:text-xl font-bold flex items-center gap-2">
                        <MapIcon className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                        <span className="hidden sm:inline">{t.titleFull}</span>
                        <span className="sm:hidden">{t.titleShort}</span>
                    </h1>
                </div>
            </div>

            {/* Metadata Panel */}
            <ComparisonMetadataPanel laws={data} matchCount={matchedIds.size} />

            {/* Toolbar */}
            <ComparisonToolbar
                syncScroll={syncScroll}
                onToggleSync={() => setSyncScroll(prev => !prev)}
            />

            {/* Split View */}
            <div className="flex-1 overflow-hidden">
                {/* Desktop: side-by-side */}
                <div className="hidden lg:grid grid-cols-2 h-full divide-x">
                    {data.map((law, i) => (
                        <ComparisonPane
                            key={law.details.law_id}
                            law={law}
                            matchedIds={matchedIds}
                            otherArticles={articleMaps[i === 0 ? 1 : 0]}
                            side={i === 0 ? 'left' : 'right'}
                            scrollRef={i === 0 ? scrollRefA : scrollRefB}
                            onScroll={() => handleScroll(i === 0 ? 'a' : 'b')}
                        />
                    ))}
                </div>

                {/* Mobile: tabs */}
                <div className="lg:hidden h-full">
                    <Tabs defaultValue={data[0]?.details.law_id} className="flex flex-col h-full">
                        <TabsList className="mx-4 mt-2 grid grid-cols-2">
                            {data.map((law) => (
                                <TabsTrigger key={law.details.law_id} value={law.details.law_id} className="truncate text-xs" title={law.details.law_name}>
                                    {law.details.law_name}
                                </TabsTrigger>
                            ))}
                        </TabsList>
                        {data.map((law, i) => (
                            <TabsContent key={law.details.law_id} value={law.details.law_id} className="flex-1 overflow-hidden mt-0">
                                <ComparisonPane
                                    law={law}
                                    matchedIds={matchedIds}
                                    otherArticles={articleMaps[i === 0 ? 1 : 0]}
                                    side={i === 0 ? 'left' : 'right'}
                                />
                            </TabsContent>
                        ))}
                    </Tabs>
                </div>
            </div>
        </div>
    );
}
