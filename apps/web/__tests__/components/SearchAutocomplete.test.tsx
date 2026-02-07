import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SearchAutocomplete } from '@/components/SearchAutocomplete';
import { LanguageProvider } from '@/components/providers/LanguageContext';

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: mockPush }),
}));

// Mock api
vi.mock('@/lib/api', () => ({
    api: {
        suggest: vi.fn(),
    },
}));

import { api } from '@/lib/api';

describe('SearchAutocomplete', () => {
    const onSearch = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders input with placeholder', () => {
        renderWithLang(<SearchAutocomplete onSearch={onSearch} placeholder="Buscar leyes..." />);
        expect(screen.getByPlaceholderText('Buscar leyes...')).toBeInTheDocument();
    });

    it('has combobox role', () => {
        renderWithLang(<SearchAutocomplete onSearch={onSearch} placeholder="Buscar..." />);
        expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('shows suggestions after typing 2+ chars', async () => {
        const mockSuggestions = [
            { id: 'ley_amparo', name: 'Ley de Amparo', tier: 'federal' },
            { id: 'ley_trabajo', name: 'Ley Federal del Trabajo', tier: 'federal' },
        ];
        (api.suggest as ReturnType<typeof vi.fn>).mockResolvedValue(mockSuggestions);

        renderWithLang(<SearchAutocomplete onSearch={onSearch} placeholder="Buscar..." />);

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'ley' } });

        await waitFor(() => {
            expect(screen.getByText('Ley de Amparo')).toBeInTheDocument();
            expect(screen.getByText('Ley Federal del Trabajo')).toBeInTheDocument();
        });
    });

    it('calls onSearch on Enter with no active suggestion', async () => {
        (api.suggest as ReturnType<typeof vi.fn>).mockResolvedValue([]);

        renderWithLang(<SearchAutocomplete onSearch={onSearch} placeholder="Buscar..." />);

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'amparo' } });
        fireEvent.keyDown(input, { key: 'Enter' });

        expect(onSearch).toHaveBeenCalledWith('amparo');
    });

    it('navigates to law on suggestion click', async () => {
        const mockSuggestions = [
            { id: 'ley_amparo', name: 'Ley de Amparo', tier: 'federal' },
        ];
        (api.suggest as ReturnType<typeof vi.fn>).mockResolvedValue(mockSuggestions);

        renderWithLang(<SearchAutocomplete onSearch={onSearch} placeholder="Buscar..." />);

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'amparo' } });

        await waitFor(() => {
            expect(screen.getByText('Ley de Amparo')).toBeInTheDocument();
        });

        // mouseDown to simulate click (onMouseDown handler)
        fireEvent.mouseDown(screen.getByText('Ley de Amparo'));

        expect(mockPush).toHaveBeenCalledWith('/leyes/ley_amparo');
    });

    it('closes dropdown on Escape', async () => {
        const mockSuggestions = [
            { id: 'ley_amparo', name: 'Ley de Amparo', tier: 'federal' },
        ];
        (api.suggest as ReturnType<typeof vi.fn>).mockResolvedValue(mockSuggestions);

        renderWithLang(<SearchAutocomplete onSearch={onSearch} placeholder="Buscar..." />);

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'amparo' } });

        await waitFor(() => {
            expect(screen.getByText('Ley de Amparo')).toBeInTheDocument();
        });

        fireEvent.keyDown(input, { key: 'Escape' });

        expect(screen.queryByText('Ley de Amparo')).not.toBeInTheDocument();
    });

    it('shows tier badges on suggestions', async () => {
        const mockSuggestions = [
            { id: 'ley_1', name: 'Ley Federal', tier: 'federal' },
            { id: 'ley_2', name: 'Código Estatal', tier: 'state' },
        ];
        (api.suggest as ReturnType<typeof vi.fn>).mockResolvedValue(mockSuggestions);

        renderWithLang(<SearchAutocomplete onSearch={onSearch} placeholder="Buscar..." />);

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'ley' } });

        await waitFor(() => {
            expect(screen.getByText('Federal')).toBeInTheDocument();
            expect(screen.getByText('Estatal')).toBeInTheDocument();
        });
    });
});
