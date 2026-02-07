'use client';

import { useState } from 'react';
import type { Article } from './types';
import { ScrollText, ChevronRight, ChevronDown, List } from 'lucide-react';
import { cn } from "@tezca/lib";
import { Button } from "@tezca/ui";
import { useLang } from '@/components/providers/LanguageContext';

const content = {
    es: {
        navLabel: 'Tabla de contenidos',
        heading: 'Tabla de Contenidos',
        noArticles: 'No se encontraron artículos.',
        fullText: 'Texto Completo',
        articlePrefix: 'Artículo',
        elements: 'elementos',
        expandAll: 'Expandir todo',
        collapseAll: 'Contraer todo',
        flatView: 'Vista plana',
        treeView: 'Vista jerárquica',
    },
    en: {
        navLabel: 'Table of contents',
        heading: 'Table of Contents',
        noArticles: 'No articles found.',
        fullText: 'Full Text',
        articlePrefix: 'Article',
        elements: 'elements',
        expandAll: 'Expand all',
        collapseAll: 'Collapse all',
        flatView: 'Flat view',
        treeView: 'Tree view',
    },
    nah: {
        navLabel: 'Tlanahuatilli amatlahcuilōlli',
        heading: 'Tlanahuatilli Amatlahcuilōlli',
        noArticles: 'Ahmo monextiā tlanahuatilli.',
        fullText: 'Mochi Tlahcuilōlli',
        articlePrefix: 'Tlanahuatilli',
        elements: 'tlamantli',
        expandAll: 'Xicpēhua mochi',
        collapseAll: 'Xictlatzacua mochi',
        flatView: 'Tlachializtli patlāhuac',
        treeView: 'Tlachializtli cuahuitl',
    },
};

interface StructureNode {
    label: string;
    children: StructureNode[];
}

interface TableOfContentsProps {
    articles: Article[];
    activeArticle: string | null;
    onArticleClick: (articleId: string) => void;
    structure?: StructureNode[];
}

function TreeNode({
    node,
    articles,
    activeArticle,
    onArticleClick,
    expanded,
    onToggle,
    depth,
    articlePrefix,
    fullTextLabel,
}: {
    node: StructureNode;
    articles: Article[];
    activeArticle: string | null;
    onArticleClick: (articleId: string) => void;
    expanded: boolean;
    onToggle: () => void;
    depth: number;
    articlePrefix: string;
    fullTextLabel: string;
}) {
    const hasChildren = node.children.length > 0;

    return (
        <div>
            <button
                onClick={onToggle}
                className={cn(
                    "group w-full flex items-center gap-1.5 px-2 py-1.5 text-sm rounded-md transition-colors text-left",
                    "text-muted-foreground hover:bg-muted hover:text-foreground",
                    depth === 0 && "font-semibold text-foreground",
                    depth === 1 && "font-medium",
                )}
                style={{ paddingLeft: `${depth * 12 + 8}px` }}
                aria-expanded={hasChildren ? expanded : undefined}
            >
                {hasChildren ? (
                    expanded ? (
                        <ChevronDown className="h-3.5 w-3.5 flex-shrink-0" />
                    ) : (
                        <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
                    )
                ) : (
                    <span className="w-3.5 flex-shrink-0" />
                )}
                <span className="truncate">{node.label}</span>
            </button>

            {expanded && hasChildren && (
                <div>
                    {node.children.map((child, i) => (
                        <ExpandableTreeNode
                            key={`${child.label}-${i}`}
                            node={child}
                            articles={articles}
                            activeArticle={activeArticle}
                            onArticleClick={onArticleClick}
                            depth={depth + 1}
                            articlePrefix={articlePrefix}
                            fullTextLabel={fullTextLabel}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

function ExpandableTreeNode(props: Omit<Parameters<typeof TreeNode>[0], 'expanded' | 'onToggle'>) {
    const [expanded, setExpanded] = useState(props.depth < 1);
    return (
        <TreeNode
            {...props}
            expanded={expanded}
            onToggle={() => setExpanded(!expanded)}
        />
    );
}

export function TableOfContents({
    articles,
    activeArticle,
    onArticleClick,
    structure,
}: TableOfContentsProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [treeView, setTreeView] = useState(!!structure?.length);

    const hasStructure = structure && structure.length > 0;

    const formatArticleLabel = (articleId: string) => {
        if (articleId === 'texto_completo' || articleId === 'full_text') return t.fullText;
        if (/^Art[ií]culo/i.test(articleId)) return articleId;
        return `${t.articlePrefix} ${articleId}`;
    };

    return (
        <nav className="h-full flex flex-col" aria-label={t.navLabel}>
            <div className="flex items-center gap-2 pb-4 mb-2 border-b">
                <ScrollText className="w-5 h-5 text-muted-foreground" />
                <h2 className="font-semibold">{t.heading}</h2>
            </div>

            {/* View toggle */}
            {hasStructure && (
                <div className="flex gap-1 mb-3">
                    <Button
                        variant={treeView ? 'default' : 'outline'}
                        size="sm"
                        className="h-7 text-xs flex-1"
                        onClick={() => setTreeView(true)}
                    >
                        {t.treeView}
                    </Button>
                    <Button
                        variant={!treeView ? 'default' : 'outline'}
                        size="sm"
                        className="h-7 text-xs flex-1"
                        onClick={() => setTreeView(false)}
                    >
                        <List className="h-3 w-3 mr-1" />
                        {t.flatView}
                    </Button>
                </div>
            )}

            <div className="flex-1 overflow-y-auto pr-2 space-y-0.5 scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent">
                {articles.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4">{t.noArticles}</p>
                ) : treeView && hasStructure ? (
                    /* Hierarchical tree view */
                    structure.map((node, i) => (
                        <ExpandableTreeNode
                            key={`${node.label}-${i}`}
                            node={node}
                            articles={articles}
                            activeArticle={activeArticle}
                            onArticleClick={onArticleClick}
                            depth={0}
                            articlePrefix={t.articlePrefix}
                            fullTextLabel={t.fullText}
                        />
                    ))
                ) : (
                    /* Flat list view */
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
                                {formatArticleLabel(article.article_id)}
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
