'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useLang } from '@/components/providers/LanguageContext';
import { API_BASE_URL } from '@/lib/config';
import type { CrossReferenceData } from '@/lib/api';

const content = {
    es: {
        viewRef: (text: string) => `Ver ${text}`,
        refLabel: (text: string) => `Referencia: ${text}`,
        referenceSingular: 'referencia detectada',
        referencePlural: 'referencias detectadas',
    },
    en: {
        viewRef: (text: string) => `View ${text}`,
        refLabel: (text: string) => `Reference: ${text}`,
        referenceSingular: 'reference detected',
        referencePlural: 'references detected',
    },
    nah: {
        viewRef: (text: string) => `Xiquitta ${text}`,
        refLabel: (text: string) => `Tlanōnōtzaliztli: ${text}`,
        referenceSingular: 'tlanōnōtzaliztli monextia',
        referencePlural: 'tlanōnōtzaliztli monextia',
    },
};

interface CrossReference {
    text: string;
    targetLawSlug?: string | null;
    targetArticle?: string | null;
    fraction?: string | null;
    confidence: number;
    startPos: number;
    endPos: number;
    targetUrl?: string | null;
}

interface LinkifiedArticleProps {
    lawId: string;
    articleId: string;
    text: string;
    minConfidence?: number;
    crossRefsDisabled?: boolean;
    /** Pre-fetched outgoing cross-references from the batch endpoint.
     *  When provided, the per-article fetch is skipped entirely. */
    preloadedRefs?: CrossReferenceData[];
}

/**
 * LinkifiedArticle - Renders article text with clickable cross-references.
 *
 * Supports two data-loading strategies:
 *
 * 1. **Batch (preferred):** Parent passes `preloadedRefs` from the batch
 *    endpoint. No per-article network request is made.
 *
 * 2. **Per-article (legacy fallback):** When `preloadedRefs` is not provided
 *    and `crossRefsDisabled` is false, fires an individual GET request.
 *    This causes N+1 on pages with many articles; avoid when possible.
 */
export function LinkifiedArticle({
    lawId,
    articleId,
    text: rawText,
    minConfidence = 0.6,
    crossRefsDisabled = true,
    preloadedRefs,
}: LinkifiedArticleProps) {
    const { lang } = useLang();
    const t = content[lang];

    // Strip leading "Articulo N." from body since the heading already shows it
    const text = rawText.replace(/^(?:Art[ií]culo|ARTÍCULO)\s+\d+[\w]*\.?\s*/i, '').trim();

    const hasPreloaded = preloadedRefs !== undefined;

    // When no preloaded data and fetch is enabled, start in loading state
    const shouldFetch = !hasPreloaded && !crossRefsDisabled;
    const [fetchedReferences, setFetchedReferences] = useState<CrossReference[]>([]);
    const [loading, setLoading] = useState(shouldFetch);

    useEffect(() => {
        // Skip fetch entirely when preloaded data is available
        if (hasPreloaded) return;
        if (crossRefsDisabled) return;

        let cancelled = false;
        const apiUrl = API_BASE_URL;

        fetch(`${apiUrl}/laws/${lawId}/articles/${articleId}/references/`)
            .then(r => r.ok ? r.json() : { outgoing: [] })
            .then(data => {
                if (!cancelled) {
                    setFetchedReferences(data.outgoing || []);
                    setLoading(false);
                }
            })
            .catch(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [lawId, articleId, crossRefsDisabled, hasPreloaded]);

    // Merge sources: preloaded takes priority over fetched
    const allReferences: CrossReference[] = hasPreloaded
        ? (preloadedRefs as CrossReference[])
        : fetchedReferences;

    // Filter by confidence threshold
    const references = allReferences.filter(ref => ref.confidence >= minConfidence);

    const buildLinkifiedText = () => {
        if (!references.length || loading) {
            return <p className="whitespace-pre-wrap leading-relaxed">{text}</p>;
        }

        const parts: React.ReactNode[] = [];
        let lastIndex = 0;

        const sorted = [...references].sort((a, b) => a.startPos - b.startPos);

        sorted.forEach((ref, i) => {
            if (ref.startPos > lastIndex) {
                parts.push(
                    <span key={`text-${i}`}>
                        {text.substring(lastIndex, ref.startPos)}
                    </span>
                );
            }

            if (ref.targetUrl) {
                parts.push(
                    <Link
                        key={`ref-${i}`}
                        href={ref.targetUrl}
                        className="text-primary underline decoration-dotted hover:decoration-solid hover:bg-primary/5 rounded px-0.5 transition-colors"
                        title={t.viewRef(ref.text)}
                    >
                        {ref.text}
                    </Link>
                );
            } else {
                parts.push(
                    <span
                        key={`ref-${i}`}
                        className="font-semibold text-primary/70"
                        title={t.refLabel(ref.text)}
                    >
                        {ref.text}
                    </span>
                );
            }

            lastIndex = ref.endPos;
        });

        if (lastIndex < text.length) {
            parts.push(
                <span key="text-end">
                    {text.substring(lastIndex)}
                </span>
            );
        }

        return <p className="whitespace-pre-wrap leading-relaxed">{parts}</p>;
    };

    return (
        <div className="prose prose-lg prose-slate dark:prose-invert max-w-none">
            {buildLinkifiedText()}

            {references.length > 0 && (
                <div className="mt-4 text-sm text-muted-foreground border-t pt-2">
                    <span className="font-medium">{references.length}</span>{' '}
                    {references.length !== 1 ? t.referencePlural : t.referenceSingular}
                </div>
            )}
        </div>
    );
}
