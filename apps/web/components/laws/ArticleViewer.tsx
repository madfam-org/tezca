'use client';

import { useEffect, useRef, useState } from 'react';
import type { Article } from "@leyesmx/lib";
import { Link as LinkIcon, Check } from 'lucide-react';
import { Card } from "@leyesmx/ui";
import { cn } from "@leyesmx/lib";
import { useInView } from 'react-intersection-observer';
import { LinkifiedArticle } from './LinkifiedArticle';

interface ArticleViewerProps {
    articles: Article[];
    activeArticle: string | null;
    lawId: string; // Added for cross-reference detection
}

export function ArticleViewer({
    articles,
    activeArticle,
    lawId
}: ArticleViewerProps) {
    const articleRefs = useRef<Record<string, HTMLElement | null>>({});
    const scrollingRef = useRef(false);

    // Handle active article visibility
    useEffect(() => {
        // Only scroll if we haven't scrolled recently (prevents fighting with user scroll)
        if (activeArticle && articleRefs.current[activeArticle] && !scrollingRef.current) {
            scrollingRef.current = true;
            articleRefs.current[activeArticle]?.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
            });
            // Reset scroll lock after animation
            setTimeout(() => {
                scrollingRef.current = false;
            }, 1000);
        }
    }, [activeArticle]);

    // Intersection observer logic could go here to update activeArticle on scroll
    // For now we trust the user clicking TOC or the initial load

    return (
        <div className="space-y-6 pb-20">
            {articles.length === 0 ? (
                <Card className="p-12 text-center text-muted-foreground">
                    No hay artículos disponibles para visualizar.
                </Card>
            ) : (
                articles.map((article) => (
                    <SingleArticle
                        key={article.article_id}
                        article={article}
                        lawId={lawId}
                        isActive={activeArticle === article.article_id}
                        setRef={(el) => {
                            articleRefs.current[article.article_id] = el;
                        }}
                    />
                ))
            )}
        </div>
    );
}

function SingleArticle({
    article,
    lawId,
    isActive,
    setRef
}: {
    article: Article;
    lawId: string;
    isActive: boolean;
    setRef: (el: HTMLElement | null) => void;
}) {
    const [copied, setCopied] = useState(false);
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

    return (
        <article
            id={`article-${article.article_id}`}
            ref={(el) => {
                setRef(el);
                ref(el);
            }}
            className={cn(
                "group relative scroll-mt-24 rounded-lg border bg-card p-6 shadow-sm transition-all",
                isActive ? "ring-2 ring-primary border-primary" : "hover:border-primary/50"
            )}
        >
            <div className="flex items-start justify-between mb-4">
                <h3 className="font-heading text-lg font-semibold text-foreground flex items-center gap-2">
                    {article.article_id === 'texto_completo' ? 'Texto Completo' : `Artículo ${article.article_id}`}
                </h3>

                <button
                    onClick={copyToClipboard}
                    className={cn(
                        "p-2 rounded-md transition-all opacity-0 group-hover:opacity-100",
                        copied
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                    )}
                    title="Copiar enlace directo"
                >
                    {copied ? <Check className="w-4 h-4" /> : <LinkIcon className="w-4 h-4" />}
                </button>
            </div>

            <LinkifiedArticle
                lawId={lawId}
                articleId={article.article_id}
                text={article.text}
            />
        </article>
    );
}
