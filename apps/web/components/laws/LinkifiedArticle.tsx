'use client';

import Link from 'next/link';
import { useLang } from '@/components/providers/LanguageContext';
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
    /** @deprecated Unused now that data is always preloaded; safe to omit. */
    lawId?: string;
    /** @deprecated Unused now that data is always preloaded; safe to omit. */
    articleId?: string;
    /** @deprecated Refs are always caller-supplied; this prop has no effect. */
    crossRefsDisabled?: boolean;
    text: string;
    minConfidence?: number;
    /** Pre-fetched outgoing cross-references from the batch endpoint.
     *  `undefined` or empty array → renders plain text. The component never
     *  fetches on its own — call sites must batch refs via useBatchCrossRefs
     *  (or equivalent) to avoid N+1 traffic. */
    preloadedRefs?: CrossReferenceData[];
}

/**
 * LinkifiedArticle — renders article text with clickable cross-references.
 *
 * Pure presentational component. Refs are passed in by the caller (typically
 * ArticleViewer's batch hook). Removing the per-article fetch path eliminates
 * the N+1 trap that was the original H3 audit finding.
 */
export function LinkifiedArticle({
    text: rawText,
    minConfidence = 0.6,
    preloadedRefs,
}: LinkifiedArticleProps) {
    const { lang } = useLang();
    const t = content[lang];

    // Strip leading "Articulo N." from body since the heading already shows it
    const text = rawText.replace(/^(?:Art[ií]culo|ARTÍCULO)\s+\d+[\w]*\.?\s*/i, '').trim();

    const allReferences: CrossReference[] = (preloadedRefs as CrossReference[] | undefined) ?? [];
    const references = allReferences.filter(ref => ref.confidence >= minConfidence);

    const buildLinkifiedText = () => {
        if (!references.length) {
            return <p className="whitespace-pre-wrap leading-relaxed">{text}</p>;
        }

        const parts: React.ReactNode[] = [];
        let lastIndex = 0;

        const sorted = [...references].sort((a, b) => a.startPos - b.startPos);

        sorted.forEach((ref) => {
            // Stable keys based on text position — survives reordering and
            // confidence-filter changes without React reconciliation glitches.
            const refKey = `${ref.startPos}-${ref.endPos}`;

            if (ref.startPos > lastIndex) {
                parts.push(
                    <span key={`text-${refKey}`}>
                        {text.substring(lastIndex, ref.startPos)}
                    </span>
                );
            }

            if (ref.targetUrl) {
                parts.push(
                    <Link
                        key={`ref-${refKey}`}
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
                        key={`ref-${refKey}`}
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
