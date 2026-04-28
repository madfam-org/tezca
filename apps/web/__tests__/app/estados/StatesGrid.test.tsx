import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

const mockGetStates = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        getStates: (...args: any[]) => mockGetStates(...args),
    },
}));

import { StatesGrid } from '@/app/estados/StatesGrid';

beforeEach(() => {
    vi.clearAllMocks();
    mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
});

afterEach(() => {
    vi.useRealTimers();
});

describe('StatesGrid', () => {
    it('renders the heading + subtitle', async () => {
        mockGetStates.mockResolvedValue({ states: [] });
        render(<StatesGrid />);
        await waitFor(() => screen.getByText(/Estados de México/i));
        expect(screen.getByText(/Explora leyes por estado/i)).toBeInTheDocument();
    });

    it('shows loading state initially', () => {
        mockGetStates.mockImplementation(() => new Promise(() => {})); // never resolves
        render(<StatesGrid />);
        expect(screen.getByText(/Cargando estados/i)).toBeInTheDocument();
    });

    it('renders the state list after fetch resolves', async () => {
        mockGetStates.mockResolvedValue({
            states: ['Aguascalientes', 'Jalisco', 'Yucatán'],
        });
        render(<StatesGrid />);
        await waitFor(() => screen.getByText('Aguascalientes'));
        expect(screen.getByText('Jalisco')).toBeInTheDocument();
        expect(screen.getByText('Yucatán')).toBeInTheDocument();
        // Count display
        expect(screen.getByText(/3 estados/i)).toBeInTheDocument();
    });

    it('renders empty-state message when API returns []', async () => {
        mockGetStates.mockResolvedValue({ states: [] });
        render(<StatesGrid />);
        await waitFor(() => screen.getByText(/No se encontraron estados/i));
    });

    it('renders error state when fetch fails', async () => {
        mockGetStates.mockRejectedValue(new Error('boom'));
        render(<StatesGrid />);
        await waitFor(() => screen.getByText(/No se pudieron cargar/i));
        expect(screen.getByText(/Reintentar/i)).toBeInTheDocument();
    });

    it('Retry button re-invokes the API', async () => {
        mockGetStates.mockRejectedValueOnce(new Error('boom'));
        mockGetStates.mockResolvedValueOnce({ states: ['Jalisco'] });

        render(<StatesGrid />);
        await waitFor(() => screen.getByText(/Reintentar/i));

        fireEvent.click(screen.getByText(/Reintentar/i));
        await waitFor(() => screen.getByText('Jalisco'));
        expect(mockGetStates).toHaveBeenCalledTimes(2);
    });

    it('renders English labels when lang is en', async () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        mockGetStates.mockResolvedValue({ states: ['Jalisco'] });
        render(<StatesGrid />);
        await waitFor(() => screen.getByText(/States of Mexico/i));
        expect(screen.getByText(/Browse laws by state/i)).toBeInTheDocument();
    });
});
