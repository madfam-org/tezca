import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { BookmarksProvider, useBookmarks } from '@/components/providers/BookmarksContext';

/** Helper to expose BookmarksContext for testing. */
function BookmarkDisplay() {
    const { bookmarks, isBookmarked, toggleBookmark, removeBookmark } = useBookmarks();
    return (
        <div>
            <span data-testid="count">{bookmarks.length}</span>
            <span data-testid="ids">{bookmarks.map((b) => b.id).join(',')}</span>
            <span data-testid="is-cpeum">{String(isBookmarked('cpeum'))}</span>
            <button data-testid="toggle-cpeum" onClick={() => toggleBookmark('cpeum', 'Constitucion')}>
                Toggle CPEUM
            </button>
            <button data-testid="toggle-lft" onClick={() => toggleBookmark('lft', 'Ley Federal del Trabajo')}>
                Toggle LFT
            </button>
            <button data-testid="remove-cpeum" onClick={() => removeBookmark('cpeum')}>
                Remove CPEUM
            </button>
        </div>
    );
}

describe('BookmarksContext', () => {
    beforeEach(() => {
        localStorage.removeItem('bookmarks');
    });

    // ---------------------------------------------------------------
    // 1. Starts with empty bookmarks
    // ---------------------------------------------------------------
    it('starts with empty bookmarks', () => {
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        expect(screen.getByTestId('count').textContent).toBe('0');
    });

    // ---------------------------------------------------------------
    // 2. Provider renders children
    // ---------------------------------------------------------------
    it('renders children correctly', () => {
        render(
            <BookmarksProvider>
                <span data-testid="child">Hello</span>
            </BookmarksProvider>,
        );

        expect(screen.getByTestId('child').textContent).toBe('Hello');
    });

    // ---------------------------------------------------------------
    // 3. Toggle adds a bookmark
    // ---------------------------------------------------------------
    it('adds a bookmark via toggleBookmark', () => {
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        expect(screen.getByTestId('count').textContent).toBe('1');
        expect(screen.getByTestId('is-cpeum').textContent).toBe('true');
    });

    // ---------------------------------------------------------------
    // 4. Toggle removes a bookmark if already present
    // ---------------------------------------------------------------
    it('removes a bookmark via toggleBookmark when already bookmarked', () => {
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        expect(screen.getByTestId('count').textContent).toBe('1');

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        expect(screen.getByTestId('count').textContent).toBe('0');
        expect(screen.getByTestId('is-cpeum').textContent).toBe('false');
    });

    // ---------------------------------------------------------------
    // 5. Multiple bookmarks
    // ---------------------------------------------------------------
    it('supports multiple bookmarks', () => {
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        fireEvent.click(screen.getByTestId('toggle-lft'));
        expect(screen.getByTestId('count').textContent).toBe('2');
        expect(screen.getByTestId('ids').textContent).toContain('cpeum');
        expect(screen.getByTestId('ids').textContent).toContain('lft');
    });

    // ---------------------------------------------------------------
    // 6. removeBookmark removes specific bookmark
    // ---------------------------------------------------------------
    it('removes specific bookmark via removeBookmark', () => {
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        fireEvent.click(screen.getByTestId('toggle-lft'));
        expect(screen.getByTestId('count').textContent).toBe('2');

        fireEvent.click(screen.getByTestId('remove-cpeum'));
        expect(screen.getByTestId('count').textContent).toBe('1');
        expect(screen.getByTestId('ids').textContent).toBe('lft');
    });

    // ---------------------------------------------------------------
    // 7. Persists to localStorage
    // ---------------------------------------------------------------
    it('persists bookmarks to localStorage', () => {
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        const stored = JSON.parse(localStorage.getItem('bookmarks') || '[]');
        expect(stored).toHaveLength(1);
        expect(stored[0].id).toBe('cpeum');
        expect(stored[0].name).toBe('Constitucion');
        expect(stored[0].bookmarkedAt).toBeDefined();
    });

    // ---------------------------------------------------------------
    // 8. Reads from localStorage on mount
    // ---------------------------------------------------------------
    it('reads bookmarks from localStorage on mount', () => {
        localStorage.setItem(
            'bookmarks',
            JSON.stringify([
                { id: 'lft', name: 'Ley Federal del Trabajo', bookmarkedAt: '2025-01-01T00:00:00Z' },
            ]),
        );

        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        expect(screen.getByTestId('count').textContent).toBe('1');
        expect(screen.getByTestId('ids').textContent).toBe('lft');
    });

    // ---------------------------------------------------------------
    // 9. isBookmarked returns false for non-bookmarked ids
    // ---------------------------------------------------------------
    it('isBookmarked returns false for non-bookmarked ids', () => {
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        expect(screen.getByTestId('is-cpeum').textContent).toBe('false');
    });

    // ---------------------------------------------------------------
    // 10. useBookmarks throws outside provider
    // ---------------------------------------------------------------
    it('useBookmarks throws when used outside BookmarksProvider', () => {
        const consoleError = console.error;
        console.error = vi.fn();

        expect(() => render(<BookmarkDisplay />)).toThrow(
            'useBookmarks must be used within BookmarksProvider',
        );

        console.error = consoleError;
    });

    // ---------------------------------------------------------------
    // 11. Handles invalid localStorage data gracefully
    // ---------------------------------------------------------------
    it('handles invalid localStorage data gracefully', () => {
        localStorage.setItem('bookmarks', 'not-valid-json');

        // Should not throw on mount
        render(
            <BookmarksProvider>
                <BookmarkDisplay />
            </BookmarksProvider>,
        );

        expect(screen.getByTestId('count').textContent).toBe('0');
    });
});
