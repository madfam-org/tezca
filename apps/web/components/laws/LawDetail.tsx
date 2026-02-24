'use client';

import { useState, useEffect, useRef } from 'react';
import { LawHeader } from './LawHeader';
import { TableOfContents } from './TableOfContents';
import { ArticleViewer } from './ArticleViewer';
import type { LawDetailData } from './types';
import { useLang } from '@/components/providers/LanguageContext';
import { Breadcrumbs } from '@/components/Breadcrumbs';
import { FontSizeControl } from '@/components/FontSizeControl';
import { api } from '@/lib/api';
import type { FontSize } from '@/components/FontSizeControl';
import { LawDetailSkeleton } from '@/components/skeletons/LawDetailSkeleton';
import { ArticleSearch } from './ArticleSearch';
import { KeyboardShortcuts } from './KeyboardShortcuts';
import { RelatedLaws } from './RelatedLaws';
import { CrossReferencePanel } from './CrossReferencePanel';
import { VersionTimeline } from './VersionTimeline';
import { recordLawView } from '@/components/RecentlyViewed';

const content = {
    es: {
        loadLawError: 'No se pudo cargar la ley',
        loadArticlesError: 'No se pudieron cargar los artículos',
        unknownError: 'Error desconocido',
        errorTitle: 'Error al cargar la ley',
        notFound: 'No se encontró la información solicitada',
        backToSearch: 'Volver al buscador',
    },
    en: {
        loadLawError: 'Could not load the law',
        loadArticlesError: 'Could not load the articles',
        unknownError: 'Unknown error',
        errorTitle: 'Error loading the law',
        notFound: 'The requested information was not found',
        backToSearch: 'Back to search',
    },
    nah: {
        loadLawError: 'Ahmo huelītic in tenahuatilli',
        loadArticlesError: 'Ahmo huelītic in tlanahuatilli',
        unknownError: 'Ahmo mati tlahtlacōlli',
        errorTitle: 'Tlahtlacōlli ic tenahuatilli',
        notFound: 'Ahmo monextiā in tlamachiliztli',
        backToSearch: 'Xicmocuepa tlatemoliztli',
    },
};

interface LawDetailProps {
    lawId: string;
}

export function LawDetail({ lawId }: LawDetailProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [data, setData] = useState<LawDetailData | null>(null);
    const [activeArticle, setActiveArticle] = useState<string | null>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [fontSize, setFontSize] = useState<FontSize>('text-base');

    useEffect(() => {
        async function fetchLaw() {
            try {
                setLoading(true);

                const [lawData, articlesData] = await Promise.all([
                    api.getLawDetail(lawId),
                    api.getLawArticles(lawId),
                ]);

                const law = lawData.law || lawData;
                const allVersions = lawData.versions || [];
                setData({
                    law,
                    version: lawData.version || (allVersions[0]) || {},
                    versions: allVersions,
                    articles: articlesData.articles ?? [],
                    total: articlesData.total ?? 0,
                });

                recordLawView({ id: law.official_id || lawId, name: law.name, tier: law.tier });

                if (window.location.hash) {
                    const articleId = window.location.hash.replace('#article-', '');
                    if (articleId) setActiveArticle(articleId);
                }
            } catch (err) {
                console.error('Failed to fetch law:', err);
                setError(err instanceof Error ? err.message : t.unknownError);
            } finally {
                setLoading(false);
            }
        }

        fetchLaw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [lawId]);

    if (loading) {
        return <LawDetailSkeleton />;
    }

    if (error || !data) {
        return (
            <div className="container mx-auto px-4 sm:px-6 py-12 flex flex-col items-center justify-center text-center">
                <h1 className="text-xl sm:text-2xl font-bold mb-2">{t.errorTitle}</h1>
                <p className="text-sm sm:text-base text-muted-foreground mb-6">{error || t.notFound}</p>
                <a
                    href="/busqueda"
                    className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                >
                    {t.backToSearch}
                </a>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background flex flex-col">
            <LawHeader law={data.law} version={data.version} />

            <div className="container mx-auto flex flex-col lg:flex-row gap-4 sm:gap-6 lg:gap-8 px-4 sm:px-6 py-6 sm:py-8 flex-1">
                {/* Left sidebar: TOC */}
                <aside className="lg:w-80 flex-shrink-0">
                    <div className="bg-card border rounded-lg p-3 sm:p-4 shadow-sm lg:sticky lg:top-24 lg:h-fit lg:max-h-[calc(100vh-8rem)]">
                        <div className="max-h-[40vh] lg:max-h-full lg:h-full overflow-y-auto">
                            <TableOfContents
                                articles={data.articles}
                                activeArticle={activeArticle}
                                onArticleClick={(id) => {
                                    setActiveArticle(id);
                                    window.history.pushState(null, '', `#article-${id}`);

                                    if (window.innerWidth < 1024) {
                                        const articleEl = document.getElementById(`article-${id}`);
                                        if (articleEl) {
                                            articleEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                        }
                                    }
                                }}
                            />
                        </div>
                    </div>
                </aside>

                {/* Main content: Articles */}
                <main className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                        <Breadcrumbs lawName={data.law.name} />
                        <FontSizeControl onChange={setFontSize} />
                    </div>
                    <div className="mb-4">
                        <ArticleSearch
                            lawId={lawId}
                            onResultClick={(articleId) => {
                                setActiveArticle(articleId);
                                window.history.pushState(null, '', `#article-${articleId}`);
                                const el = document.getElementById(`article-${articleId}`);
                                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }}
                        />
                    </div>
                    <div className={fontSize}>
                        <ArticleViewer
                            articles={data.articles}
                            activeArticle={activeArticle}
                            lawId={lawId}
                            lawName={data.law.name}
                            publicationDate={data.version.publication_date}
                            tier={data.law.tier}
                        />
                    </div>
                    <KeyboardShortcuts
                        articles={data.articles}
                        activeArticle={activeArticle}
                        onArticleChange={(articleId) => {
                            setActiveArticle(articleId);
                            window.history.pushState(null, '', `#article-${articleId}`);
                            const el = document.getElementById(`article-${articleId}`);
                            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        onFocusSearch={() => searchInputRef.current?.focus()}
                        lawId={lawId}
                    />
                    <CrossReferencePanel lawId={lawId} />
                    <VersionTimeline versions={data.versions} />
                    <RelatedLaws lawId={lawId} />
                </main>
            </div>
        </div>
    );
}
