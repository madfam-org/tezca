import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseLang = vi.fn(() => ({ lang: 'es' as const, setLang: vi.fn() }));
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: (...args: any[]) => mockUseLang(...args),
}));

import LawArticles from '@/components/LawArticles';

const ORIGINAL_FETCH = global.fetch;

const SAMPLE_DATA = {
    law_id: 'cpeum',
    total_articles: 2,
    total_transitorios: 1,
    articles: [
        { id: 'a1', number: 'Artículo 1', content: 'El contenido del primero', type: 'article' },
        { id: 'a2', number: 'Artículo 2', content: 'Lorem ipsum dolor sit amet', type: 'article' },
        { id: 't1', number: 'Transitorio Primero', content: 'Vigente al día siguiente', type: 'transitorio' },
    ],
};

beforeEach(() => {
    vi.clearAllMocks();
    mockUseLang.mockReturnValue({ lang: 'es', setLang: vi.fn() });
});

afterEach(() => {
    global.fetch = ORIGINAL_FETCH;
});

describe('LawArticles', () => {
    it('shows loading state before data resolves', () => {
        global.fetch = vi.fn(() => new Promise(() => {})) as any; // never resolves
        render(<LawArticles lawId="cpeum" />);
        expect(screen.getByText(/Cargando artículos/i)).toBeInTheDocument();
    });

    it('renders articles after fetch succeeds', async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => SAMPLE_DATA,
        }) as any;
        render(<LawArticles lawId="cpeum" />);

        await waitFor(() => {
            expect(screen.getByText('Artículo 1')).toBeInTheDocument();
        });
        expect(screen.getByText('Artículo 2')).toBeInTheDocument();
    });

    it('shows error state when fetch fails', async () => {
        global.fetch = vi.fn().mockResolvedValue({ ok: false }) as any;
        render(<LawArticles lawId="cpeum" />);
        await waitFor(() => {
            expect(screen.getByText(/Error al cargar/i)).toBeInTheDocument();
        });
    });

    it('shows error state on network exception', async () => {
        global.fetch = vi.fn().mockRejectedValue(new Error('network')) as any;
        render(<LawArticles lawId="cpeum" />);
        await waitFor(() => {
            expect(screen.getByText(/Error al cargar/i)).toBeInTheDocument();
        });
    });

    it('filters articles by search query', async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => SAMPLE_DATA,
        }) as any;
        render(<LawArticles lawId="cpeum" />);
        await waitFor(() => screen.getByText('Artículo 1'));

        const input = screen.getByPlaceholderText(/Buscar/i);
        fireEvent.change(input, { target: { value: 'Lorem' } });

        // Article 2 contains "Lorem" → present
        expect(screen.getByText('Artículo 2')).toBeInTheDocument();
        // Article 1 doesn't → gone
        expect(screen.queryByText('Artículo 1')).not.toBeInTheDocument();
    });

    it('toggles to transitorios view', async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => SAMPLE_DATA,
        }) as any;
        render(<LawArticles lawId="cpeum" />);
        await waitFor(() => screen.getByText('Artículo 1'));

        const toggle = screen.getByText(/Ver Transitorios/);
        fireEvent.click(toggle);

        expect(screen.getByText('Transitorio Primero')).toBeInTheDocument();
        expect(screen.queryByText('Artículo 1')).not.toBeInTheDocument();
    });

    it('shows no-results message when search yields nothing', async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => SAMPLE_DATA,
        }) as any;
        render(<LawArticles lawId="cpeum" />);
        await waitFor(() => screen.getByText('Artículo 1'));

        fireEvent.change(screen.getByPlaceholderText(/Buscar/i), {
            target: { value: 'xyz_no_match_xyz' },
        });

        expect(screen.getByText(/No se encontraron/i)).toBeInTheDocument();
    });

    it('renders articles in English when lang is en', async () => {
        mockUseLang.mockReturnValue({ lang: 'en', setLang: vi.fn() });
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => SAMPLE_DATA,
        }) as any;
        render(<LawArticles lawId="cpeum" />);
        await waitFor(() => screen.getByText('Artículo 1'));

        expect(screen.getByText(/View Transitory/i)).toBeInTheDocument();
    });
});
