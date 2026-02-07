import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SearchFilters, type SearchFilterState } from '@/components/SearchFilters';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { api } from '@/lib/api';

// Mock the API
vi.mock('@/lib/api', () => ({
    api: {
        getStates: vi.fn().mockResolvedValue({ states: [] }),
        getMunicipalities: vi.fn().mockResolvedValue([]),
    },
}));

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe('SearchFilters', () => {
    const mockFilters: SearchFilterState = {
        jurisdiction: ['federal'],
        category: null,
        state: null,
        municipality: null,
        status: 'all',
        sort: 'relevance',
        title: '',
        chapter: '',
        law_type: 'all',
    };

    const mockOnChange = vi.fn();

    beforeEach(() => {
        mockOnChange.mockReset();
        vi.mocked(api.getStates).mockResolvedValue({ states: [] });
    });

    it('renders jurisdiction options', async () => {
        await act(async () => {
            renderWithLang(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);
        });

        expect(screen.getByRole('button', { name: /Federal/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Estatal/i })).toBeInTheDocument();
    });

    it('calls onFiltersChange when jurisdiction changes', async () => {
        await act(async () => {
            renderWithLang(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);
        });

        const federalButton = screen.getByRole('button', { name: /Federal/i });
        fireEvent.click(federalButton);

        expect(mockOnChange).toHaveBeenCalled();
    });

    it('shows state dropdown when state jurisdiction is selected', async () => {
        const mockGetStates = vi.mocked(api.getStates);
        mockGetStates.mockResolvedValue({ states: ['Colima', 'Jalisco'] });

        await act(async () => {
            renderWithLang(<SearchFilters filters={{ ...mockFilters, jurisdiction: ['state'] }} onFiltersChange={mockOnChange} resultCount={10} />);
        });

        expect(await screen.findByText('Estado')).toBeInTheDocument();
        expect(mockGetStates).toHaveBeenCalled();
    });

    describe('Structural Filters', () => {
        it('renders title and chapter inputs', async () => {
            await act(async () => {
                renderWithLang(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);
            });

            expect(screen.getByPlaceholderText(/Filtrar por t.tulo/i)).toBeInTheDocument();
            expect(screen.getByPlaceholderText(/Filtrar por cap.tulo/i)).toBeInTheDocument();
        });

        it('calls onFiltersChange when title input changes', async () => {
            await act(async () => {
                renderWithLang(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);
            });

            const titleInput = screen.getByPlaceholderText(/Filtrar por t.tulo/i);
            fireEvent.change(titleInput, { target: { value: 'Titulo I' } });

            expect(mockOnChange).toHaveBeenCalledWith(expect.objectContaining({
                title: 'Titulo I'
            }));
        });
    });
});
