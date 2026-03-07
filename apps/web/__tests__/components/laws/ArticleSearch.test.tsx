import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ArticleSearch } from '@/components/laws/ArticleSearch';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
    api: {
        searchWithinLaw: vi.fn(),
    },
}));

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe('ArticleSearch', () => {
    const mockOnResultClick = vi.fn();

    beforeEach(() => {
        vi.mocked(api.searchWithinLaw).mockReset();
        mockOnResultClick.mockReset();
        vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('renders search input with placeholder', () => {
        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        expect(screen.getByPlaceholderText('Buscar dentro de esta ley...')).toBeInTheDocument();
    });

    it('debounces search on input change', async () => {
        vi.mocked(api.searchWithinLaw).mockResolvedValue({
            total: 1,
            results: [{ article_id: '5', snippet: 'texto encontrado', score: 9.5 }],
        });

        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        const input = screen.getByPlaceholderText('Buscar dentro de esta ley...');

        // Type a query
        await act(async () => {
            await userEvent.type(input, 'amparo', { delay: 10 });
        });

        // Should not have been called yet (debounce is 300ms)
        expect(api.searchWithinLaw).not.toHaveBeenCalled();

        // Advance past debounce
        await act(async () => {
            vi.advanceTimersByTime(350);
        });

        await waitFor(() => {
            expect(api.searchWithinLaw).toHaveBeenCalledWith('cpeum', 'amparo');
        });
    });

    it('renders search results with article IDs', async () => {
        vi.mocked(api.searchWithinLaw).mockResolvedValue({
            total: 2,
            results: [
                { article_id: '107', snippet: 'juicio de <em>amparo</em>', score: 9.0 },
                { article_id: '103', snippet: 'tribunales <em>amparo</em>', score: 8.5 },
            ],
        });

        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        const input = screen.getByPlaceholderText('Buscar dentro de esta ley...');
        await act(async () => {
            await userEvent.type(input, 'amparo', { delay: 10 });
            vi.advanceTimersByTime(350);
        });

        await waitFor(() => {
            expect(screen.getByText('Art. 107')).toBeInTheDocument();
            expect(screen.getByText('Art. 103')).toBeInTheDocument();
        });
    });

    it('sanitizes HTML in snippets', async () => {
        vi.mocked(api.searchWithinLaw).mockResolvedValue({
            total: 1,
            results: [
                { article_id: '1', snippet: '<em>amparo</em><script>alert(1)</script>', score: 9.0 },
            ],
        });

        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        const input = screen.getByPlaceholderText('Buscar dentro de esta ley...');
        await act(async () => {
            await userEvent.type(input, 'amp', { delay: 10 });
            vi.advanceTimersByTime(350);
        });

        await waitFor(() => {
            expect(screen.getByText('Art. 1')).toBeInTheDocument();
        });

        // Script tag should be stripped by DOMPurify
        expect(document.querySelector('script')).toBeNull();
    });

    it('calls onResultClick when result clicked', async () => {
        vi.mocked(api.searchWithinLaw).mockResolvedValue({
            total: 1,
            results: [{ article_id: '42', snippet: 'result text', score: 8.0 }],
        });

        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        const input = screen.getByPlaceholderText('Buscar dentro de esta ley...');
        await act(async () => {
            await userEvent.type(input, 'test', { delay: 10 });
            vi.advanceTimersByTime(350);
        });

        await waitFor(() => {
            expect(screen.getByText('Art. 42')).toBeInTheDocument();
        });

        await act(async () => {
            await userEvent.click(screen.getByText('Art. 42'));
        });

        expect(mockOnResultClick).toHaveBeenCalledWith('42');
    });

    it('shows no results message', async () => {
        vi.mocked(api.searchWithinLaw).mockResolvedValue({
            total: 0,
            results: [],
        });

        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        const input = screen.getByPlaceholderText('Buscar dentro de esta ley...');
        await act(async () => {
            await userEvent.type(input, 'xyz', { delay: 10 });
            vi.advanceTimersByTime(350);
        });

        await waitFor(() => {
            expect(screen.getByText('Sin resultados')).toBeInTheDocument();
        });
    });

    it('handles API error gracefully', async () => {
        vi.mocked(api.searchWithinLaw).mockRejectedValue(new Error('API down'));

        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        const input = screen.getByPlaceholderText('Buscar dentro de esta ley...');
        await act(async () => {
            await userEvent.type(input, 'test', { delay: 10 });
            vi.advanceTimersByTime(350);
        });

        // Should not crash; results should remain empty
        await waitFor(() => {
            expect(screen.queryByText('Art.')).not.toBeInTheDocument();
        });
    });

    it('clear button resets search state', async () => {
        vi.mocked(api.searchWithinLaw).mockResolvedValue({
            total: 1,
            results: [{ article_id: '1', snippet: 'found', score: 9.0 }],
        });

        renderWithLang(
            <ArticleSearch lawId="cpeum" onResultClick={mockOnResultClick} />
        );

        const input = screen.getByPlaceholderText('Buscar dentro de esta ley...');
        await act(async () => {
            await userEvent.type(input, 'test', { delay: 10 });
            vi.advanceTimersByTime(350);
        });

        await waitFor(() => {
            expect(screen.getByText('Art. 1')).toBeInTheDocument();
        });

        // Click clear button
        const clearBtn = screen.getByLabelText('Limpiar busqueda');
        await act(async () => {
            await userEvent.click(clearBtn);
        });

        // Results should be gone and input cleared
        expect(screen.queryByText('Art. 1')).not.toBeInTheDocument();
        expect(input).toHaveValue('');
    });
});
