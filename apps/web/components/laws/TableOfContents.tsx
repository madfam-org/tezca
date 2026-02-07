'use client';

import type { Article } from './types';
import { ScrollText, ChevronRight } from 'lucide-react';
import { cn } from "@tezca/lib";
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        navLabel: 'Tabla de contenidos',
        heading: 'Tabla de Contenidos',
        noArticles: 'No se encontraron artículos.',
        fullText: 'Texto Completo',
        articlePrefix: 'Artículo',
        elements: 'elementos',
    },
    en: {
        navLabel: 'Table of contents',
        heading: 'Table of Contents',
        noArticles: 'No articles found.',
        fullText: 'Full Text',
        articlePrefix: 'Article',
        elements: 'elements',
    },
};

interface TableOfContentsProps {
    articles: Article[];
    activeArticle: string | null;
    onArticleClick: (articleId: string) => void;
}

export function TableOfContents({
    articles,
    activeArticle,
    onArticleClick
}: TableOfContentsProps) {
    const { lang } = useLang();
    const t = content[lang];

    return (
        <nav className="h-full flex flex-col" aria-label={t.navLabel}>
            <div className="flex items-center gap-2 pb-4 mb-2 border-b">
                <ScrollText className="w-5 h-5 text-muted-foreground" />
                <h2 className="font-semibold">{t.heading}</h2>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-1 scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent">
                {articles.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4">{t.noArticles}</p>
                ) : (
                    articles.map((article) => (
                        <button
                            key={article.article_id}
                            onClick={() => onArticleClick(article.article_id)}
                            className={cn(
                                "group w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors",
                                activeArticle === article.article_id
                                    ? "bg-primary/10 text-primary font-medium"
                                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                            )}
                        >
                            <span className="truncate mr-2">
                                {article.article_id === 'texto_completo' || article.article_id === 'full_text'
                                    ? t.fullText
                                    : /^Art[ií]culo/i.test(article.article_id)
                                        ? article.article_id
                                        : `${t.articlePrefix} ${article.article_id}`}
                            </span>
                            {activeArticle === article.article_id && (
                                <ChevronRight className="w-4 h-4 text-primary" />
                            )}
                        </button>
                    ))
                )}
            </div>

            <div className="pt-4 border-t mt-2">
                <p className="text-xs text-muted-foreground text-center">
                    {articles.length} {t.elements}
                </p>
            </div>
        </nav>
    );
}
