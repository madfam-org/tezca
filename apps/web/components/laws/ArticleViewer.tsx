'use client';

import { useEffect, useRef, useState } from 'react';
import type { Article } from "@tezca/lib";
import { Link as LinkIcon, Check, Quote } from 'lucide-react';
import { Card } from "@tezca/ui";
import { cn } from "@tezca/lib";
import { useInView } from 'react-intersection-observer';
import { LinkifiedArticle } from './LinkifiedArticle';
import { useLang, type Lang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        noArticles: 'No hay artículos disponibles para visualizar.',
        fullText: 'Texto Completo',
        articlePrefix: 'Artículo',
        copyLink: 'Copiar enlace directo al artículo',
        copyLinkShort: 'Copiar enlace directo',
        copyCitation: 'Copiar cita',
        citationCopied: 'Cita copiada',
    },
    en: {
        noArticles: 'No articles available to display.',
        fullText: 'Full Text',
        articlePrefix: 'Article',
        copyLink: 'Copy direct link to article',
        copyLinkShort: 'Copy direct link',
        copyCitation: 'Copy citation',
        citationCopied: 'Citation copied',
    },
    nah: {
        noArticles: 'Ahmo oncah tlanahuatilli ic tlachiyaliztli.',
        fullText: 'Mochi Tlahcuilōlli',
        articlePrefix: 'Tlanahuatilli',
        copyLink: 'Xiccopīna tlanahuatilli tlahcuilōltzintli',
        copyLinkShort: 'Xiccopīna tlahcuilōltzintli',
        copyCitation: 'Xiccopīna tlanāhuatīlli',
        citationCopied: 'Ōmocopīnac',
    },
};

interface ArticleViewerProps {
    articles: Article[];
    activeArticle: string | null;
    lawId: string;
    lawName?: string;
}

export function ArticleViewer({
    articles,
    activeArticle,
    lawId,
    lawName,
}: ArticleViewerProps) {
    const { lang } = useLang();
    const t = content[lang];
    const articleRefs = useRef<Record<string, HTMLElement | null>>({});
    const scrollingRef = useRef(false);

    useEffect(() => {
        if (activeArticle && articleRefs.current[activeArticle] && !scrollingRef.current) {
            scrollingRef.current = true;
            articleRefs.current[activeArticle]?.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
            });
            setTimeout(() => {
                scrollingRef.current = false;
            }, 1000);
        }
    }, [activeArticle]);

    return (
        <div className="space-y-6 pb-20">
            {articles.length === 0 ? (
                <Card className="p-12 text-center text-muted-foreground">
                    {t.noArticles}
                </Card>
            ) : (
                articles.map((article) => (
                    <SingleArticle
                        key={article.article_id}
                        article={article}
                        lawId={lawId}
                        lawName={lawName}
                        isActive={activeArticle === article.article_id}
                        setRef={(el) => {
                            articleRefs.current[article.article_id] = el;
                        }}
                        lang={lang}
                    />
                ))
            )}
        </div>
    );
}

function SingleArticle({
    article,
    lawId,
    lawName,
    isActive,
    setRef,
    lang,
}: {
    article: Article;
    lawId: string;
    lawName?: string;
    isActive: boolean;
    setRef: (el: HTMLElement | null) => void;
    lang: Lang;
}) {
    const t = content[lang];
    const [copied, setCopied] = useState(false);
    const [citationCopied, setCitationCopied] = useState(false);
    const { ref } = useInView({
        threshold: 0.5,
        triggerOnce: false
    });

    const copyToClipboard = () => {
        const url = `${window.location.origin}${window.location.pathname}#article-${article.article_id}`;
        navigator.clipboard.writeText(url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const copyCitation = () => {
        const artNum = article.article_id.replace(/^Art[ií]culo\s*/i, '');
        const name = lawName || lawId;
        const citation = `Art. ${artNum}, ${name}`;
        navigator.clipboard.writeText(citation);
        setCitationCopied(true);
        setTimeout(() => setCitationCopied(false), 2000);
    };

    const articleLabel = article.article_id === 'texto_completo' || article.article_id === 'full_text'
        ? t.fullText
        : /^Art[ií]culo/i.test(article.article_id)
            ? article.article_id
            : `${t.articlePrefix} ${article.article_id}`;

    return (
        <article
            id={`article-${article.article_id}`}
            ref={(el) => {
                setRef(el);
                ref(el);
            }}
            aria-label={articleLabel}
            className={cn(
                "group relative scroll-mt-24 rounded-lg border bg-card p-6 shadow-sm transition-all",
                isActive ? "ring-2 ring-primary border-primary" : "hover:border-primary/50"
            )}
        >
            <div className="flex items-start justify-between mb-4">
                <h3 className="font-heading text-lg font-semibold text-foreground flex items-center gap-2">
                    {articleLabel}
                </h3>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                    <button
                        onClick={copyCitation}
                        className={cn(
                            "p-2 rounded-md transition-all",
                            citationCopied
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                        )}
                        aria-label={t.copyCitation}
                        title={citationCopied ? t.citationCopied : t.copyCitation}
                    >
                        {citationCopied ? <Check className="w-4 h-4" /> : <Quote className="w-4 h-4" />}
                    </button>
                    <button
                        onClick={copyToClipboard}
                        className={cn(
                            "p-2 rounded-md transition-all",
                            copied
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                        )}
                        aria-label={t.copyLink}
                        title={t.copyLinkShort}
                    >
                        {copied ? <Check className="w-4 h-4" /> : <LinkIcon className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            <LinkifiedArticle
                lawId={lawId}
                articleId={article.article_id}
                text={article.text}
            />
        </article>
    );
}
