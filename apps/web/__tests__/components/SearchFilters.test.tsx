import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
        status: 'all',
        sort: 'relevance',
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
});
