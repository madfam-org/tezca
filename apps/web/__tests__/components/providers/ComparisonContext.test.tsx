import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ComparisonProvider, useComparison } from '@/components/providers/ComparisonContext';

/** Helper to expose ComparisonContext for testing. */
function ComparisonDisplay() {
    const { selectedLaws, toggleLaw, clearSelection, isLawSelected } = useComparison();
    return (
        <div>
            <span data-testid="count">{selectedLaws.length}</span>
            <span data-testid="ids">{selectedLaws.join(',')}</span>
            <span data-testid="is-cpeum">{String(isLawSelected('cpeum'))}</span>
            <span data-testid="is-lft">{String(isLawSelected('lft'))}</span>
            <button data-testid="toggle-cpeum" onClick={() => toggleLaw('cpeum')}>Toggle CPEUM</button>
            <button data-testid="toggle-lft" onClick={() => toggleLaw('lft')}>Toggle LFT</button>
            <button data-testid="toggle-lgpas" onClick={() => toggleLaw('lgpas')}>Toggle LGPAS</button>
            <button data-testid="clear" onClick={clearSelection}>Clear</button>
        </div>
    );
}

describe('ComparisonContext', () => {
    beforeEach(() => {
        localStorage.removeItem('comparison_selected_laws');
    });

    // ---------------------------------------------------------------
    // 1. Starts with empty selection
    // ---------------------------------------------------------------
    it('starts with empty selection', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        expect(screen.getByTestId('count').textContent).toBe('0');
    });

    // ---------------------------------------------------------------
    // 2. Provider renders children
    // ---------------------------------------------------------------
    it('renders children correctly', () => {
        render(
            <ComparisonProvider>
                <span data-testid="child">Content</span>
            </ComparisonProvider>,
        );

        expect(screen.getByTestId('child').textContent).toBe('Content');
    });

    // ---------------------------------------------------------------
    // 3. Toggle adds a law
    // ---------------------------------------------------------------
    it('adds a law via toggleLaw', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        expect(screen.getByTestId('count').textContent).toBe('1');
        expect(screen.getByTestId('is-cpeum').textContent).toBe('true');
    });

    // ---------------------------------------------------------------
    // 4. Toggle removes a law
    // ---------------------------------------------------------------
    it('removes a law via toggleLaw when already selected', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        expect(screen.getByTestId('is-cpeum').textContent).toBe('true');

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        expect(screen.getByTestId('is-cpeum').textContent).toBe('false');
        expect(screen.getByTestId('count').textContent).toBe('0');
    });

    // ---------------------------------------------------------------
    // 5. Max 2 laws — adding third replaces first
    // ---------------------------------------------------------------
    it('enforces max of 2 selected laws, removing first when adding third', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        fireEvent.click(screen.getByTestId('toggle-lft'));
        expect(screen.getByTestId('count').textContent).toBe('2');

        // Adding a third should remove the first (cpeum) and keep lft + lgpas
        fireEvent.click(screen.getByTestId('toggle-lgpas'));
        expect(screen.getByTestId('count').textContent).toBe('2');
        expect(screen.getByTestId('is-cpeum').textContent).toBe('false');
        expect(screen.getByTestId('is-lft').textContent).toBe('true');
        expect(screen.getByTestId('ids').textContent).toContain('lgpas');
    });

    // ---------------------------------------------------------------
    // 6. clearSelection clears all
    // ---------------------------------------------------------------
    it('clears all selected laws', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        fireEvent.click(screen.getByTestId('toggle-lft'));
        expect(screen.getByTestId('count').textContent).toBe('2');

        fireEvent.click(screen.getByTestId('clear'));
        expect(screen.getByTestId('count').textContent).toBe('0');
    });

    // ---------------------------------------------------------------
    // 7. isLawSelected returns false for non-selected
    // ---------------------------------------------------------------
    it('isLawSelected returns false for non-selected laws', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        expect(screen.getByTestId('is-cpeum').textContent).toBe('false');
        expect(screen.getByTestId('is-lft').textContent).toBe('false');
    });

    // ---------------------------------------------------------------
    // 8. Persists selection to localStorage
    // ---------------------------------------------------------------
    it('persists selection to localStorage on change', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        // Wait for useEffect to run
        const stored = JSON.parse(localStorage.getItem('comparison_selected_laws') || '[]');
        expect(stored).toContain('cpeum');
    });

    // ---------------------------------------------------------------
    // 9. Reads from localStorage on mount
    // ---------------------------------------------------------------
    it('reads from localStorage on mount', () => {
        localStorage.setItem('comparison_selected_laws', JSON.stringify(['lft']));

        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        expect(screen.getByTestId('count').textContent).toBe('1');
        expect(screen.getByTestId('is-lft').textContent).toBe('true');
    });

    // ---------------------------------------------------------------
    // 10. useComparison throws outside provider
    // ---------------------------------------------------------------
    it('useComparison throws when used outside ComparisonProvider', () => {
        const consoleError = console.error;
        console.error = vi.fn();

        expect(() => render(<ComparisonDisplay />)).toThrow(
            'useComparison must be used within a ComparisonProvider',
        );

        console.error = consoleError;
    });

    // ---------------------------------------------------------------
    // 11. Clear persists empty array
    // ---------------------------------------------------------------
    it('clears selection and persists empty array', () => {
        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        fireEvent.click(screen.getByTestId('toggle-cpeum'));
        fireEvent.click(screen.getByTestId('clear'));

        const stored = JSON.parse(localStorage.getItem('comparison_selected_laws') || '[]');
        expect(stored).toEqual([]);
    });

    // ---------------------------------------------------------------
    // 12. Handles invalid localStorage gracefully
    // ---------------------------------------------------------------
    it('handles invalid localStorage gracefully', () => {
        localStorage.setItem('comparison_selected_laws', 'not-json');

        render(
            <ComparisonProvider>
                <ComparisonDisplay />
            </ComparisonProvider>,
        );

        // Falls back to empty — getInitialLaws catches JSON.parse error
        expect(screen.getByTestId('count').textContent).toBe('0');
    });
});
