'use client';

import { RefObject, useMemo } from 'react';
import { Badge } from "@tezca/ui";
import { diffWords } from 'diff';
import type { ComparisonLawData, LawStructureNode } from './types';

interface ComparisonPaneProps {
    law: ComparisonLawData;
    matchedIds: Set<string>;
    /** Articles from the other law, keyed by article_id, for diff highlighting */
    otherArticles?: Map<string, string>;
    /** Side identifier for diff coloring */
    side?: 'left' | 'right';
    scrollRef?: RefObject<HTMLDivElement | null>;
    onScroll?: () => void;
}

/**
 * Render word-level diff between two article texts.
 * Added words are green, removed words are red with strikethrough.
 */
function DiffText({ thisText, otherText }: { thisText: string; otherText: string }) {
    const parts = useMemo(() => diffWords(otherText, thisText), [thisText, otherText]);

    return (
        <p className="whitespace-pre-wrap leading-relaxed text-xs sm:text-sm">
            {parts.map((part, i) => {
                if (part.added) {
                    return (
                        <span key={i} className="bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded-sm px-0.5">
                            {part.value}
                        </span>
                    );
                }
                if (part.removed) {
                    return (
                        <span key={i} className="bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 line-through rounded-sm px-0.5">
                            {part.value}
                        </span>
                    );
                }
                return <span key={i}>{part.value}</span>;
            })}
        </p>
    );
}

export function ComparisonPane({ law, matchedIds, otherArticles, side, scrollRef, onScroll }: ComparisonPaneProps) {
    // Count articles unique to this side
    const uniqueCount = law.details.articles.filter(a => !matchedIds.has(a.article_id)).length;

    return (
        <div className="flex flex-col h-full overflow-hidden">
            {/* Law Header */}
            <div className="p-3 sm:p-4 bg-muted/30 border-b">
                <h2 className="text-sm sm:text-base font-bold truncate" title={law.details.law_name}>
                    {law.details.law_name}
                </h2>
                <div className="flex gap-2 mt-1">
                    <Badge variant="outline" className="text-xs">
                        {law.details.total} artículos
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                        {matchedIds.size} en común
                    </Badge>
                    {uniqueCount > 0 && (
                        <Badge
                            variant="outline"
                            className={`text-xs ${side === 'left' ? 'border-green-500 text-green-700 dark:text-green-400' : 'border-blue-500 text-blue-700 dark:text-blue-400'}`}
                        >
                            {uniqueCount} únicos
                        </Badge>
                    )}
                </div>
            </div>

            {/* Content & Structure */}
            <div className="flex-1 overflow-hidden flex">
                {/* Structure Sidebar */}
                <div className="w-1/3 border-r overflow-y-auto bg-muted/10 p-2 hidden xl:block text-xs">
                    <h3 className="font-semibold mb-2 text-muted-foreground uppercase tracking-wider text-xs">
                        Estructura
                    </h3>
                    <StructureTree nodes={law.structure} />
                </div>

                {/* Article List */}
                <div
                    ref={scrollRef}
                    onScroll={onScroll}
                    className="flex-1 p-3 sm:p-4 overflow-y-auto"
                >
                    <div className="prose dark:prose-invert max-w-none text-xs sm:text-sm">
                        {law.details.articles.map(article => {
                            const isMatched = matchedIds.has(article.article_id);
                            const isUnique = !isMatched;
                            const otherText = otherArticles?.get(article.article_id);
                            const hasDiff = isMatched && otherText && otherText !== article.text;

                            return (
                                <div
                                    key={article.article_id}
                                    className={`mb-4 ${
                                        isMatched
                                            ? 'border-l-2 border-primary pl-2'
                                            : side === 'left'
                                                ? 'border-l-2 border-green-500 pl-2 bg-green-50/50 dark:bg-green-900/10'
                                                : 'border-l-2 border-blue-500 pl-2 bg-blue-50/50 dark:bg-blue-900/10'
                                    }`}
                                >
                                    <span className="font-bold text-primary block mb-1 sticky top-0 bg-background/90 backdrop-blur z-10 text-xs sm:text-sm">
                                        {article.article_id}
                                        {isUnique && (
                                            <Badge
                                                variant="outline"
                                                className={`ml-2 text-xs ${
                                                    side === 'left'
                                                        ? 'border-green-500 text-green-600'
                                                        : 'border-blue-500 text-blue-600'
                                                }`}
                                            >
                                                {side === 'left' ? 'Solo aquí' : 'Solo aquí'}
                                            </Badge>
                                        )}
                                        {hasDiff && (
                                            <Badge variant="outline" className="ml-2 text-xs border-amber-500 text-amber-600">
                                                Diferencias
                                            </Badge>
                                        )}
                                    </span>
                                    {hasDiff && otherText ? (
                                        <DiffText thisText={article.text} otherText={otherText} />
                                    ) : (
                                        <p className="whitespace-pre-wrap text-muted-foreground leading-relaxed text-xs sm:text-sm">
                                            {article.text}
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

function StructureTree({ nodes, level = 0 }: { nodes: LawStructureNode[]; level?: number }) {
    if (!nodes || nodes.length === 0) {
        return <div className="text-muted-foreground italic pl-2">Sin estructura</div>;
    }

    return (
        <ul className={`space-y-1 ${level > 0 ? 'ml-2 border-l pl-2' : ''}`}>
            {nodes.map((node, i) => (
                <li key={`${level}-${i}-${node.label}`}>
                    <div className="py-1 px-2 rounded hover:bg-muted cursor-pointer truncate" title={node.label}>
                        {node.label}
                    </div>
                    {node.children && node.children.length > 0 && (
                        <StructureTree nodes={node.children} level={level + 1} />
                    )}
                </li>
            ))}
        </ul>
    );
}
