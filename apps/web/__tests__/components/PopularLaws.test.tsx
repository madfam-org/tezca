import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Badge: ({ children, className }: { children: React.ReactNode; className?: string }) => (
        <span data-testid="badge" className={className}>{children}</span>
    ),
}));

// Mock config
vi.mock('@/lib/config', () => ({
    API_BASE_URL: 'http://localhost:8000/api/v1',
}));

import { PopularLaws } from '@/components/PopularLaws';

describe('PopularLaws', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('renders section title', () => {
        vi.spyOn(global, 'fetch').mockResolvedValue(
            new Response(JSON.stringify({ existing: [] }), { status: 200 }),
        );
        render(<PopularLaws />);
        expect(screen.getByText('Leyes Populares')).toBeInTheDocument();
    });

    it('renders subtitle', () => {
        vi.spyOn(global, 'fetch').mockResolvedValue(
            new Response(JSON.stringify({ existing: [] }), { status: 200 }),
        );
        render(<PopularLaws />);
        expect(screen.getByText('Acceso rápido a las leyes más consultadas')).toBeInTheDocument();
    });

    it('renders all 8 popular law badges before API responds', () => {
        // Never-resolving fetch to test initial render
        vi.spyOn(global, 'fetch').mockReturnValue(new Promise(() => {}));
        render(<PopularLaws />);
        expect(screen.getByText('Constitución')).toBeInTheDocument();
        expect(screen.getByText('Código Civil Federal')).toBeInTheDocument();
        expect(screen.getByText('Código Penal Federal')).toBeInTheDocument();
        expect(screen.getByText('ISR')).toBeInTheDocument();
        expect(screen.getByText('IVA')).toBeInTheDocument();
        expect(screen.getByText('Ley Federal del Trabajo')).toBeInTheDocument();
        expect(screen.getByText('Seguro Social')).toBeInTheDocument();
        expect(screen.getByText('Amparo')).toBeInTheDocument();
    });

    it('links to correct law detail pages using short IDs', () => {
        vi.spyOn(global, 'fetch').mockReturnValue(new Promise(() => {}));
        render(<PopularLaws />);

        const expectedLinks = [
            { name: 'Constitución', href: '/leyes/cpeum' },
            { name: 'Código Civil Federal', href: '/leyes/ccf' },
            { name: 'Código Penal Federal', href: '/leyes/cpf' },
            { name: 'ISR', href: '/leyes/lisr' },
            { name: 'IVA', href: '/leyes/liva' },
            { name: 'Ley Federal del Trabajo', href: '/leyes/lft' },
            { name: 'Seguro Social', href: '/leyes/lss' },
            { name: 'Amparo', href: '/leyes/amparo' },
        ];

        for (const { name, href } of expectedLinks) {
            const link = screen.getByText(name).closest('a');
            expect(link?.getAttribute('href')).toBe(href);
        }
    });

    it('does not use mx-fed- prefix in hrefs', () => {
        vi.spyOn(global, 'fetch').mockReturnValue(new Promise(() => {}));
        render(<PopularLaws />);
        const links = screen.getAllByRole('link');
        for (const link of links) {
            expect(link.getAttribute('href')).not.toContain('mx-fed-');
        }
    });

    it('renders 8 badge elements before API responds', () => {
        vi.spyOn(global, 'fetch').mockReturnValue(new Promise(() => {}));
        render(<PopularLaws />);
        const badges = screen.getAllByTestId('badge');
        expect(badges).toHaveLength(8);
    });

    it('filters to only existing laws after API responds', async () => {
        vi.spyOn(global, 'fetch').mockResolvedValue(
            new Response(
                JSON.stringify({ existing: ['cpeum', 'ccf', 'lft'] }),
                { status: 200 },
            ),
        );
        render(<PopularLaws />);

        await waitFor(() => {
            expect(screen.getAllByTestId('badge')).toHaveLength(3);
        });

        expect(screen.getByText('Constitución')).toBeInTheDocument();
        expect(screen.getByText('Código Civil Federal')).toBeInTheDocument();
        expect(screen.getByText('Ley Federal del Trabajo')).toBeInTheDocument();
        expect(screen.queryByText('ISR')).not.toBeInTheDocument();
    });

    it('keeps all badges when API returns empty existing array', async () => {
        vi.spyOn(global, 'fetch').mockResolvedValue(
            new Response(JSON.stringify({ existing: [] }), { status: 200 }),
        );
        render(<PopularLaws />);

        // Wait for useEffect to complete
        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalled();
        });

        // All badges should still be rendered (graceful degradation)
        expect(screen.getAllByTestId('badge')).toHaveLength(8);
    });

    it('keeps all badges when API fails', async () => {
        vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Network error'));
        render(<PopularLaws />);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalled();
        });

        // All badges should still be rendered (graceful degradation)
        expect(screen.getAllByTestId('badge')).toHaveLength(8);
    });

    it('keeps all badges when API returns non-OK status', async () => {
        vi.spyOn(global, 'fetch').mockResolvedValue(
            new Response('Server Error', { status: 500 }),
        );
        render(<PopularLaws />);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalled();
        });

        expect(screen.getAllByTestId('badge')).toHaveLength(8);
    });

    it('calls the correct API URL with all law IDs', () => {
        const fetchSpy = vi.spyOn(global, 'fetch').mockReturnValue(new Promise(() => {}));
        render(<PopularLaws />);

        expect(fetchSpy).toHaveBeenCalledWith(
            'http://localhost:8000/api/v1/laws/exists/?ids=cpeum,ccf,cpf,lisr,liva,lft,lss,amparo',
        );
    });
});
