import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock BookmarksContext
const mockToggleBookmark = vi.fn();
vi.mock('@/components/providers/BookmarksContext', () => ({
    useBookmarks: () => ({
        bookmarks: [],
        isBookmarked: vi.fn(() => false),
        toggleBookmark: mockToggleBookmark,
        removeBookmark: vi.fn(),
    }),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Keyboard: ({ className }: any) => <span data-testid="keyboard-icon" className={className} />,
}));

import { KeyboardShortcuts } from '@/components/laws/KeyboardShortcuts';
import { useLang } from '@/components/providers/LanguageContext';

const articles = [
    { article_id: 'art-1', text: 'Article 1 text' },
    { article_id: 'art-2', text: 'Article 2 text' },
    { article_id: 'art-3', text: 'Article 3 text' },
];

describe('KeyboardShortcuts', () => {
    const onArticleChange = vi.fn();
    const onFocusSearch = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    // ---------------------------------------------------------------
    // 1. Renders toggle button
    // ---------------------------------------------------------------
    it('renders the toggle button with correct aria-label', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        expect(screen.getByLabelText('Mostrar/ocultar atajos')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 2. Panel hidden by default
    // ---------------------------------------------------------------
    it('shortcuts panel is hidden by default', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        expect(screen.queryByText('Atajos de teclado')).not.toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 3. Clicking toggle shows panel
    // ---------------------------------------------------------------
    it('clicking toggle button shows shortcuts panel', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.click(screen.getByLabelText('Mostrar/ocultar atajos'));
        expect(screen.getByText('Atajos de teclado')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 4. Panel shows all shortcuts
    // ---------------------------------------------------------------
    it('panel shows all shortcut descriptions', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.click(screen.getByLabelText('Mostrar/ocultar atajos'));
        expect(screen.getByText('Siguiente artículo')).toBeInTheDocument();
        expect(screen.getByText('Artículo anterior')).toBeInTheDocument();
        expect(screen.getByText('Buscar en esta ley')).toBeInTheDocument();
        expect(screen.getByText('Agregar/quitar favorito')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 5. "j" key navigates to next article
    // ---------------------------------------------------------------
    it('"j" key navigates to next article', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle="art-1"
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.keyDown(document, { key: 'j' });
        expect(onArticleChange).toHaveBeenCalledWith('art-2');
    });

    // ---------------------------------------------------------------
    // 6. "k" key navigates to previous article
    // ---------------------------------------------------------------
    it('"k" key navigates to previous article', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle="art-2"
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.keyDown(document, { key: 'k' });
        expect(onArticleChange).toHaveBeenCalledWith('art-1');
    });

    // ---------------------------------------------------------------
    // 7. "j" wraps around at end
    // ---------------------------------------------------------------
    it('"j" wraps to first article from last', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle="art-3"
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.keyDown(document, { key: 'j' });
        expect(onArticleChange).toHaveBeenCalledWith('art-1');
    });

    // ---------------------------------------------------------------
    // 8. "k" wraps around at beginning
    // ---------------------------------------------------------------
    it('"k" wraps to last article from first', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle="art-1"
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.keyDown(document, { key: 'k' });
        expect(onArticleChange).toHaveBeenCalledWith('art-3');
    });

    // ---------------------------------------------------------------
    // 9. "/" key focuses search
    // ---------------------------------------------------------------
    it('"/" key focuses search', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.keyDown(document, { key: '/' });
        expect(onFocusSearch).toHaveBeenCalledOnce();
    });

    // ---------------------------------------------------------------
    // 10. "b" key toggles bookmark
    // ---------------------------------------------------------------
    it('"b" key toggles bookmark', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.keyDown(document, { key: 'b' });
        expect(mockToggleBookmark).toHaveBeenCalledWith('cpeum', '');
    });

    // ---------------------------------------------------------------
    // 11. "?" toggles panel
    // ---------------------------------------------------------------
    it('"?" key toggles shortcuts panel', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        // Open panel
        fireEvent.keyDown(document, { key: '?' });
        expect(screen.getByText('Atajos de teclado')).toBeInTheDocument();

        // Close panel
        fireEvent.keyDown(document, { key: '?' });
        expect(screen.queryByText('Atajos de teclado')).not.toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 12. Escape closes panel
    // ---------------------------------------------------------------
    it('Escape key closes shortcuts panel', () => {
        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        // Open panel
        fireEvent.click(screen.getByLabelText('Mostrar/ocultar atajos'));
        expect(screen.getByText('Atajos de teclado')).toBeInTheDocument();

        // Escape closes it
        fireEvent.keyDown(document, { key: 'Escape' });
        expect(screen.queryByText('Atajos de teclado')).not.toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 13. Does not fire on input elements
    // ---------------------------------------------------------------
    it('does not fire shortcuts when typing in an input', () => {
        render(
            <div>
                <input data-testid="text-input" />
                <KeyboardShortcuts
                    articles={articles}
                    activeArticle={null}
                    onArticleChange={onArticleChange}
                    onFocusSearch={onFocusSearch}
                    lawId="cpeum"
                />
            </div>,
        );

        const input = screen.getByTestId('text-input');
        input.focus();
        fireEvent.keyDown(input, { key: 'j' });
        expect(onArticleChange).not.toHaveBeenCalled();
    });

    // ---------------------------------------------------------------
    // 14. English labels
    // ---------------------------------------------------------------
    it('renders English labels when lang is en', () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });

        render(
            <KeyboardShortcuts
                articles={articles}
                activeArticle={null}
                onArticleChange={onArticleChange}
                onFocusSearch={onFocusSearch}
                lawId="cpeum"
            />,
        );

        fireEvent.click(screen.getByLabelText('Show/hide shortcuts'));
        expect(screen.getByText('Keyboard shortcuts')).toBeInTheDocument();
        expect(screen.getByText('Next article')).toBeInTheDocument();
    });
});
