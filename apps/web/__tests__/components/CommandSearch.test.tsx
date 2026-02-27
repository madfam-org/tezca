import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    useRouter: vi.fn(() => ({ push: mockPush })),
    usePathname: vi.fn(() => '/'),
    useSearchParams: vi.fn(() => new URLSearchParams()),
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock api with controllable suggest
const mockSuggest = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        suggest: (...args: unknown[]) => mockSuggest(...args),
    },
}));

import { CommandSearchTrigger } from '@/components/CommandSearch';

describe('CommandSearchTrigger', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockSuggest.mockResolvedValue([]);
    });

    it('renders search button with aria-label', () => {
        render(<CommandSearchTrigger />);
        expect(screen.getByLabelText('Buscar leyes y artículos...')).toBeInTheDocument();
    });

    it('renders keyboard shortcut hint', () => {
        render(<CommandSearchTrigger />);
        expect(screen.getByText('K')).toBeInTheDocument();
    });

    it('opens dialog on button click', () => {
        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('opens dialog on Cmd+K', () => {
        render(<CommandSearchTrigger />);
        fireEvent.keyDown(document, { key: 'k', metaKey: true });
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('opens dialog on Ctrl+K', () => {
        render(<CommandSearchTrigger />);
        fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
        expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('closes dialog on Escape', () => {
        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));
        expect(screen.getByRole('dialog')).toBeInTheDocument();

        fireEvent.keyDown(document, { key: 'Escape' });
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('closes dialog on close button click', () => {
        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));
        expect(screen.getByRole('dialog')).toBeInTheDocument();

        fireEvent.click(screen.getByLabelText('Cerrar búsqueda'));
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('shows search input with combobox role', () => {
        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));
        expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('displays suggestions after typing', async () => {
        mockSuggest.mockResolvedValue([
            { id: 'cpeum', name: 'Constitución', tier: 'federal' },
        ]);

        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'const' } });

        await waitFor(() => {
            expect(screen.getByText('Constitución')).toBeInTheDocument();
        }, { timeout: 2000 });
    });

    it('does not search with less than 2 characters', async () => {
        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'c' } });

        // Wait longer than debounce
        await new Promise(r => setTimeout(r, 400));
        expect(mockSuggest).not.toHaveBeenCalled();
    });

    it('shows "view all results" link when query has text', async () => {
        mockSuggest.mockResolvedValue([]);

        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'test' } });

        // "View all" appears immediately when query has text, independent of suggestions
        await waitFor(() => {
            expect(screen.getByText(/Ver todos los resultados/)).toBeInTheDocument();
        }, { timeout: 2000 });
    });

    it('navigates to law on suggestion click', async () => {
        mockSuggest.mockResolvedValue([
            { id: 'cpeum', name: 'Constitución', tier: 'federal' },
        ]);

        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'const' } });

        await waitFor(() => {
            expect(screen.getByText('Constitución')).toBeInTheDocument();
        }, { timeout: 2000 });

        fireEvent.click(screen.getByText('Constitución'));

        expect(mockPush).toHaveBeenCalledWith('/leyes/cpeum');
    });

    it('navigates to search results on Enter with no selection', () => {
        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'amparo' } });

        // Arrow down to "view all" (index 0 since no suggestions loaded yet), then Enter
        fireEvent.keyDown(input, { key: 'ArrowDown' });
        fireEvent.keyDown(input, { key: 'Enter' });

        expect(mockPush).toHaveBeenCalledWith('/busqueda?q=amparo');
    });

    it('renders keyboard hint footer', () => {
        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));

        expect(screen.getByText('navegar')).toBeInTheDocument();
        expect(screen.getByText('seleccionar')).toBeInTheDocument();
        expect(screen.getByText('cerrar')).toBeInTheDocument();
    });

    it('shows no results message for empty search', async () => {
        mockSuggest.mockResolvedValue([]);

        render(<CommandSearchTrigger />);
        fireEvent.click(screen.getByLabelText('Buscar leyes y artículos...'));

        const input = screen.getByRole('combobox');
        fireEvent.change(input, { target: { value: 'zzzzzzz' } });

        await waitFor(() => {
            expect(screen.getByText(/Sin resultados para/)).toBeInTheDocument();
        }, { timeout: 2000 });
    });
});
