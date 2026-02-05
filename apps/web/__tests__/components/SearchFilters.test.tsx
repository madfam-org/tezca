import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchFilters, type SearchFilterState } from '@/components/SearchFilters';
import { api } from '@/lib/api';

// Mock the API
vi.mock('@/lib/api', () => ({
    api: {
        getStates: vi.fn().mockResolvedValue({ states: [] }),
    },
}));

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
    };

    const mockOnChange = vi.fn();

    it('renders jurisdiction options', () => {
        mockFilters.jurisdiction = ['federal'];
        render(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);

        expect(screen.getByRole('button', { name: /Federal/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Estatal/i })).toBeInTheDocument();
    });

    it('calls onFiltersChange when jurisdiction changes', () => {
        render(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);

        const federalButton = screen.getByRole('button', { name: /Federal/i });
        fireEvent.click(federalButton);

        expect(mockOnChange).toHaveBeenCalled();
    });

    it('shows state dropdown when state jurisdiction is selected', async () => {
        // Setup mock
        const mockGetStates = vi.mocked(api.getStates);
        mockGetStates.mockResolvedValue({ states: ['Colima', 'Jalisco'] });

        // Initial render with federal only
        render(<SearchFilters filters={{ ...mockFilters, jurisdiction: ['state'] }} onFiltersChange={mockOnChange} resultCount={10} />);

        // Find label
        expect(await screen.findByText('Estado')).toBeInTheDocument();

        // Verify API called
        expect(mockGetStates).toHaveBeenCalled();
    });

    describe('Structural Filters', () => {
        it('renders title and chapter inputs', () => {
            render(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);
            
            expect(screen.getByPlaceholderText(/Filtrar por título/i)).toBeInTheDocument();
            expect(screen.getByPlaceholderText(/Filtrar por capítulo/i)).toBeInTheDocument();
        });

        it('calls onFiltersChange when title input changes', () => {
            render(<SearchFilters filters={mockFilters} onFiltersChange={mockOnChange} resultCount={10} />);
            
            const titleInput = screen.getByPlaceholderText(/Filtrar por título/i);
            fireEvent.change(titleInput, { target: { value: 'Titulo I' } });

            expect(mockOnChange).toHaveBeenCalledWith(expect.objectContaining({
                title: 'Titulo I'
            }));
        });
    });
});
