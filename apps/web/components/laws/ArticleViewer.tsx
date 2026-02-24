'use client';

import { useEffect, useRef, useState } from 'react';
import type { Article } from "@tezca/lib";
import { Link as LinkIcon, Check, Quote, BookOpen } from 'lucide-react';
import { Card } from "@tezca/ui";
import { cn } from "@tezca/lib";
import { useInView } from 'react-intersection-observer';
import { LinkifiedArticle } from './LinkifiedArticle';
import { useLang, LOCALE_MAP, type Lang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        noArticles: 'No hay artículos disponibles para visualizar.',
        fullText: 'Texto Completo',
        articlePrefix: 'Artículo',
        copyLink: 'Copiar enlace directo al artículo',
        copyLinkShort: 'Copiar enlace directo',
        copyCitation: 'Copiar cita legal',
        copyCitationBibtex: 'Copiar cita BibTeX',
        citationCopied: 'Cita copiada',
        bibtexCopied: 'BibTeX copiado',
        linkCopied: 'Enlace copiado',
    },
    en: {
        noArticles: 'No articles available to display.',
        fullText: 'Full Text',
        articlePrefix: 'Article',
        copyLink: 'Copy direct link to article',
        copyLinkShort: 'Copy direct link',
        copyCitation: 'Copy legal citation',
        copyCitationBibtex: 'Copy BibTeX citation',
        citationCopied: 'Citation copied',
        bibtexCopied: 'BibTeX copied',
        linkCopied: 'Link copied',
    },
    nah: {
        noArticles: 'Ahmo oncah tlanahuatilli ic tlachiyaliztli.',
        fullText: 'Mochi Tlahcuilōlli',
        articlePrefix: 'Tlanahuatilli',
        copyLink: 'Xiccopīna tlanahuatilli tlahcuilōltzintli',
        copyLinkShort: 'Xiccopīna tlahcuilōltzintli',
        copyCitation: 'Xiccopīna tlanāhuatīlli',
        copyCitationBibtex: 'Xiccopīna BibTeX',
        citationCopied: 'Ōmocopīnac',
        bibtexCopied: 'BibTeX ōmocopīnac',
        linkCopied: 'Tlahcuilōltzintli ōmocopīnac',
    },
};

interface ArticleViewerProps {
    articles: Article[];
    activeArticle: string | null;
    lawId: string;
    lawName?: string;
    publicationDate?: string | null;
    tier?: string;
}

export function ArticleViewer({
    articles,
    activeArticle,
    lawId,
    lawName,
    publicationDate,
    tier,
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
                        publicationDate={publicationDate}
                        tier={tier}
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

function formatDofDate(dateStr: string | null | undefined, locale: string): string {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return `DOF ${date.toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' })}`;
    } catch {
        return '';
    }
}

function buildCitationText(
    articleId: string,
    lawName: string,
    publicationDate: string | null | undefined,
    locale: string,
): string {
    const artNum = articleId.replace(/^Art[ií]culo\s*/i, '');
    const parts = [`Art. ${artNum}`, lawName];
    const dofDate = formatDofDate(publicationDate, locale);
    if (dofDate) parts.push(dofDate);
    return parts.join(', ');
}

function buildBibtexCitation(
    articleId: string,
    lawId: string,
    lawName: string,
    publicationDate: string | null | undefined,
    tier: string | undefined,
): string {
    const artNum = articleId.replace(/^Art[ií]culo\s*/i, '');
    const year = publicationDate ? new Date(publicationDate).getFullYear() : new Date().getFullYear();
    const key = `${lawId.replace(/[^a-zA-Z0-9]/g, '_')}_art${artNum}`;
    const jurisdiction = tier === 'state' ? 'Estatal' : tier === 'municipal' ? 'Municipal' : 'Federal';

    return `@misc{${key},
  title = {Art. ${artNum}, ${lawName}},
  author = {{Congreso de la Unión}},
  year = {${year}},
  howpublished = {${jurisdiction}},
  note = {Disponible en https://tezca.mx/leyes/${encodeURIComponent(lawId)}},
}`;
}

function SingleArticle({
    article,
    lawId,
    lawName,
    publicationDate,
    tier,
    isActive,
    setRef,
    lang,
}: {
    article: Article;
    lawId: string;
    lawName?: string;
    publicationDate?: string | null;
    tier?: string;
    isActive: boolean;
    setRef: (el: HTMLElement | null) => void;
    lang: Lang;
}) {
    const t = content[lang];
    const locale = LOCALE_MAP[lang];
    const [copiedState, setCopiedState] = useState<'none' | 'citation' | 'bibtex' | 'link'>('none');
    const { ref } = useInView({
        threshold: 0.5,
        triggerOnce: false
    });

    const clearCopied = () => setTimeout(() => setCopiedState('none'), 2000);

    const copyToClipboard = () => {
        const url = `${window.location.origin}${window.location.pathname}#article-${article.article_id}`;
        navigator.clipboard.writeText(url);
        setCopiedState('link');
        clearCopied();
    };

    const copyCitation = () => {
        const name = lawName || lawId;
        const citation = buildCitationText(article.article_id, name, publicationDate, locale);
        navigator.clipboard.writeText(citation);
        setCopiedState('citation');
        clearCopied();
    };

    const copyBibtex = () => {
        const name = lawName || lawId;
        const bibtex = buildBibtexCitation(article.article_id, lawId, name, publicationDate, tier);
        navigator.clipboard.writeText(bibtex);
        setCopiedState('bibtex');
        clearCopied();
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
                "group relative scroll-mt-24 rounded-lg border bg-card p-4 sm:p-6 shadow-sm transition-all",
                isActive ? "ring-2 ring-primary border-primary" : "hover:border-primary/50"
            )}
        >
            <div className="flex items-start justify-between mb-4">
                <h3 className="font-heading text-lg font-semibold text-foreground flex items-center gap-2">
                    {articleLabel}
                </h3>

                <div className="flex items-center gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 focus-within:opacity-100 transition-all">
                    {/* Copy legal citation */}
                    <button
                        onClick={copyCitation}
                        className={cn(
                            "p-2 rounded-md transition-all",
                            copiedState === 'citation'
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                        )}
                        aria-label={t.copyCitation}
                        title={copiedState === 'citation' ? t.citationCopied : t.copyCitation}
                    >
                        {copiedState === 'citation' ? <Check className="w-4 h-4" /> : <Quote className="w-4 h-4" />}
                    </button>
                    {/* Copy BibTeX */}
                    <button
                        onClick={copyBibtex}
                        className={cn(
                            "p-2 rounded-md transition-all",
                            copiedState === 'bibtex'
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                        )}
                        aria-label={t.copyCitationBibtex}
                        title={copiedState === 'bibtex' ? t.bibtexCopied : t.copyCitationBibtex}
                    >
                        {copiedState === 'bibtex' ? <Check className="w-4 h-4" /> : <BookOpen className="w-4 h-4" />}
                    </button>
                    {/* Copy direct link */}
                    <button
                        onClick={copyToClipboard}
                        className={cn(
                            "p-2 rounded-md transition-all",
                            copiedState === 'link'
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                        )}
                        aria-label={t.copyLink}
                        title={copiedState === 'link' ? t.linkCopied : t.copyLinkShort}
                    >
                        {copiedState === 'link' ? <Check className="w-4 h-4" /> : <LinkIcon className="w-4 h-4" />}
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
