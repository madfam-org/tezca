'use client';

import { RefObject } from 'react';
import { Badge } from "@leyesmx/ui";
import type { ComparisonLawData, LawStructureNode } from './types';

interface ComparisonPaneProps {
    law: ComparisonLawData;
    matchedIds: Set<string>;
    scrollRef?: RefObject<HTMLDivElement | null>;
    onScroll?: () => void;
}

export function ComparisonPane({ law, matchedIds, scrollRef, onScroll }: ComparisonPaneProps) {
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
                </div>
            </div>

            {/* Content & Structure */}
            <div className="flex-1 overflow-hidden flex">
                {/* Structure Sidebar */}
                <div className="w-1/3 border-r overflow-y-auto bg-muted/10 p-2 hidden xl:block text-xs">
                    <h3 className="font-semibold mb-2 text-muted-foreground uppercase tracking-wider text-[10px]">
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
                        {law.details.articles.map(article => (
                            <div
                                key={article.article_id}
                                className={`mb-4 ${matchedIds.has(article.article_id) ? 'border-l-2 border-primary pl-2' : ''}`}
                            >
                                <span className="font-bold text-primary block mb-1 sticky top-0 bg-background/90 backdrop-blur z-10 text-xs sm:text-sm">
                                    {article.article_id}
                                </span>
                                <p className="whitespace-pre-wrap text-muted-foreground leading-relaxed text-xs sm:text-sm">
                                    {article.text}
                                </p>
                            </div>
                        ))}
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
                <li key={i}>
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
