'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface CrossReference {
    text: string;
    targetLawSlug?: string;
    targetArticle?: string;
    fraction?: string;
    confidence: number;
    startPos: number;
    endPos: number;
    targetUrl?: string;
}

interface LinkifiedArticleProps {
    lawId: string;
    articleId: string;
    text: string;
}

/**
 * LinkifiedArticle - Renders article text with clickable cross-references
 * 
 * Fetches cross-references from API and makes legal references clickable.
 * Example: "artículo 5 de la Ley de Amparo" becomes a clickable link.
 */
export function LinkifiedArticle({ lawId, articleId, text }: LinkifiedArticleProps) {
    const [references, setReferences] = useState<CrossReference[]>([]);
    const [loading, setLoading] = useState(true);
    const [, setHoveredRef] = useState<string | null>(null);
    
    useEffect(() => {
        // Fetch cross-references for this article
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        
        fetch(`${apiUrl}/api/v1/laws/${lawId}/articles/${articleId}/references/`)
            .then(r => r.ok ? r.json() : { outgoing: [] })
            .then(data => {
                setReferences(data.outgoing || []);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to load cross-references:', err);
                setLoading(false);
            });
    }, [lawId, articleId]);
    
    /**
     * Build linkified text by replacing reference positions with clickable links
     */
    const buildLinkifiedText = () => {
        // If no references or still loading, return plain text
        if (!references.length || loading) {
            return <p className="whitespace-pre-wrap leading-relaxed">{text}</p>;
        }
        
        const parts: React.ReactNode[] = [];
        let lastIndex = 0;
        
        // Sort references by position to process in order
        const sorted = [...references].sort((a, b) => a.startPos - b.startPos);
        
        sorted.forEach((ref, i) => {
            // Add text before this reference
            if (ref.startPos > lastIndex) {
                parts.push(
                    <span key={`text-${i}`}>
                        {text.substring(lastIndex, ref.startPos)}
                    </span>
                );
            }
            
            // Add the linked reference
            const refKey = `${ref.targetLawSlug}-${ref.targetArticle}`;
            
            if (ref.targetUrl) {
                parts.push(
                    <Link
                        key={`ref-${i}`}
                        href={ref.targetUrl}
                        className="text-primary underline decoration-dotted hover:decoration-solid hover:bg-primary/5 rounded px-0.5 transition-colors"
                        onMouseEnter={() => setHoveredRef(refKey)}
                        onMouseLeave={() => setHoveredRef(null)}
                        title={`Ver ${ref.text}`}
                    >
                        {ref.text}
                    </Link>
                );
            } else {
                // No target URL - render as emphasized but not clickable
                parts.push(
                    <span
                        key={`ref-${i}`}
                        className="font-semibold text-primary/70"
                        title={`Referencia: ${ref.text}`}
                    >
                        {ref.text}
                    </span>
                );
            }
            
            lastIndex = ref.endPos;
        });
        
        // Add remaining text after last reference
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
            
            {/* Show reference count if available */}
            {references.length > 0 && (
                <div className="mt-4 text-sm text-muted-foreground border-t pt-2">
                    <span className="font-medium">{references.length}</span> referencia
                    {references.length !== 1 ? 's' : ''} detectada
                    {references.length !== 1 ? 's' : ''}
                </div>
            )}
        </div>
    );
}
