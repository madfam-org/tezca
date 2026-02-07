'use client';

import { useEffect, useState } from 'react';
import { Keyboard } from 'lucide-react';
import { useLang } from '@/components/providers/LanguageContext';
import { useBookmarks } from '@/components/providers/BookmarksContext';
import type { Article } from '@tezca/lib';

const content = {
    es: {
        title: 'Atajos de teclado',
        next: 'Siguiente articulo',
        prev: 'Articulo anterior',
        search: 'Buscar en esta ley',
        bookmark: 'Agregar/quitar favorito',
        close: 'Cerrar panel',
        toggle: 'Mostrar/ocultar atajos',
    },
    en: {
        title: 'Keyboard shortcuts',
        next: 'Next article',
        prev: 'Previous article',
        search: 'Search within this law',
        bookmark: 'Toggle bookmark',
        close: 'Close panel',
        toggle: 'Show/hide shortcuts',
    },
};

interface KeyboardShortcutsProps {
    articles: Article[];
    activeArticle: string | null;
    onArticleChange: (articleId: string) => void;
    onFocusSearch: () => void;
    lawId: string;
}

export function KeyboardShortcuts({
    articles,
    activeArticle,
    onArticleChange,
    onFocusSearch,
    lawId,
}: KeyboardShortcutsProps) {
    const { lang } = useLang();
    const t = content[lang];
    const [showPanel, setShowPanel] = useState(false);
    const { toggleBookmark } = useBookmarks();

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            const target = e.target as HTMLElement;
            const isTyping = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

            if (e.key === 'Escape') {
                setShowPanel(false);
                return;
            }

            if (isTyping) return;

            if (e.key === '?') {
                e.preventDefault();
                setShowPanel((prev) => !prev);
                return;
            }

            if (e.key === '/') {
                e.preventDefault();
                onFocusSearch();
                return;
            }

            if (e.key === 'b') {
                e.preventDefault();
                toggleBookmark(lawId, '');
                return;
            }

            if (e.key === 'j' || e.key === 'k') {
                e.preventDefault();
                if (articles.length === 0) return;

                const currentIndex = activeArticle
                    ? articles.findIndex((a) => a.article_id === activeArticle)
                    : -1;

                let nextIndex: number;
                if (e.key === 'j') {
                    nextIndex = currentIndex < articles.length - 1 ? currentIndex + 1 : 0;
                } else {
                    nextIndex = currentIndex > 0 ? currentIndex - 1 : articles.length - 1;
                }

                onArticleChange(articles[nextIndex].article_id);
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [articles, activeArticle, onArticleChange, onFocusSearch, toggleBookmark, lawId]);

    return (
        <>
            {/* Floating hint button */}
            <button
                onClick={() => setShowPanel((prev) => !prev)}
                className="fixed bottom-20 right-4 z-30 rounded-full bg-card border shadow-lg p-2 text-muted-foreground hover:text-foreground transition-colors"
                aria-label={t.toggle}
                title={t.toggle}
            >
                <Keyboard className="h-4 w-4" />
            </button>

            {/* Shortcuts panel */}
            {showPanel && (
                <div className="fixed bottom-32 right-4 z-30 w-64 rounded-lg border bg-card shadow-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-semibold">{t.title}</h4>
                        <button
                            onClick={() => setShowPanel(false)}
                            className="text-muted-foreground hover:text-foreground text-xs"
                        >
                            Esc
                        </button>
                    </div>
                    <div className="space-y-2 text-xs">
                        {[
                            ['j', t.next],
                            ['k', t.prev],
                            ['/', t.search],
                            ['b', t.bookmark],
                            ['?', t.toggle],
                            ['Esc', t.close],
                        ].map(([key, desc]) => (
                            <div key={key} className="flex items-center justify-between">
                                <kbd className="px-1.5 py-0.5 rounded bg-muted font-mono text-[10px]">{key}</kbd>
                                <span className="text-muted-foreground">{desc}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    );
}
