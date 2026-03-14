import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: any) => <a href={href} {...props}>{children}</a>,
}));

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => <div data-testid="card" className={className}>{children}</div>,
    CardContent: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

// Mock LanguageContext
vi.mock('@/components/providers/LanguageContext', () => ({
    useLang: vi.fn(() => ({ lang: 'es', setLang: vi.fn() })),
    LOCALE_MAP: { es: 'es-MX', en: 'en-US', nah: 'es-MX' },
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
    Building2: ({ className }: any) => <span data-testid="building-icon" className={className} />,
    Scale: ({ className }: any) => <span data-testid="scale-icon" className={className} />,
    Home: ({ className }: any) => <span data-testid="home-icon" className={className} />,
}));

const mockGetStats = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        getStats: (...args: any[]) => mockGetStats(...args),
    },
}));

import { JurisdictionCards } from '@/components/JurisdictionCards';
import { useLang } from '@/components/providers/LanguageContext';

const MOCK_STATS = {
    total_laws: 35000,
    federal_count: 2000,
    state_count: 30000,
    municipal_count: 3000,
    legislative_count: 20000,
    non_legislative_count: 15000,
    total_articles: 1000000,
    federal_coverage: 90,
    state_coverage: 85,
    municipal_coverage: 30,
    total_coverage: 75,
    last_update: '2026-03-01',
    recent_laws: [],
    coverage: {
        leyes_vigentes: { count: 35000, universe: 45000, percentage: 78 },
        federal: { count: 2000, universe: 2500, percentage: 80 },
        state: { count: 30000, universe: 35000, percentage: 86 },
        municipal: {
            count: 3000,
            universe: null,
            percentage: null,
            cities_covered: 150,
            total_municipalities: 2469,
        },
    },
};

describe('JurisdictionCards', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'es', setLang: vi.fn() });
    });

    // ---------------------------------------------------------------
    // 1. Shows loading skeletons initially
    // ---------------------------------------------------------------
    it('shows loading skeletons before data loads', () => {
        mockGetStats.mockReturnValue(new Promise(() => {}));
        render(<JurisdictionCards />);

        expect(screen.getByText('Cobertura por Jurisdicción')).toBeInTheDocument();
        // 3 skeleton cards
        const skeletons = document.querySelectorAll('.animate-pulse');
        expect(skeletons.length).toBeGreaterThanOrEqual(3);
    });

    // ---------------------------------------------------------------
    // 2. Shows error message on failure
    // ---------------------------------------------------------------
    it('shows error message when API fails', async () => {
        mockGetStats.mockRejectedValue(new Error('Fail'));
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText('No se pudieron cargar las estadísticas.')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 3. Renders heading and subtitle
    // ---------------------------------------------------------------
    it('renders heading and subtitle', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText('Cobertura por Jurisdicción')).toBeInTheDocument();
            expect(screen.getByText('Explora leyes federales, estatales y municipales')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 4. Renders three jurisdiction cards
    // ---------------------------------------------------------------
    it('renders Federal, Estatal, and Municipal cards', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText('Federal')).toBeInTheDocument();
            expect(screen.getByText('Estatal')).toBeInTheDocument();
            expect(screen.getByText('Municipal')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 5. Shows law counts
    // ---------------------------------------------------------------
    it('shows law counts per jurisdiction', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText('2,000')).toBeInTheDocument();
            expect(screen.getByText('30,000')).toBeInTheDocument();
            expect(screen.getByText('3,000')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 6. Shows "leyes" label
    // ---------------------------------------------------------------
    it('shows "leyes" label for each card', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            const leyesLabels = screen.getAllByText('leyes');
            expect(leyesLabels.length).toBe(3);
        });
    });

    // ---------------------------------------------------------------
    // 7. Cards link to correct href
    // ---------------------------------------------------------------
    it('cards link to jurisdiction-filtered browse page', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            const links = document.querySelectorAll('a[href]');
            const hrefs = Array.from(links).map((l) => l.getAttribute('href'));
            expect(hrefs).toContain('/leyes?jurisdiction=federal');
            expect(hrefs).toContain('/leyes?jurisdiction=state');
            expect(hrefs).toContain('/leyes?jurisdiction=municipal');
        });
    });

    // ---------------------------------------------------------------
    // 8. Shows municipal coverage with cities covered
    // ---------------------------------------------------------------
    it('shows municipal coverage with cities covered', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText(/150/)).toBeInTheDocument();
            expect(screen.getByText(/municipios cubiertos/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 9. Shows federal/state coverage percentages
    // ---------------------------------------------------------------
    it('shows federal and state coverage percentages', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText('80%')).toBeInTheDocument();
            expect(screen.getByText('86%')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 10. Shows non-legislative count for state
    // ---------------------------------------------------------------
    it('shows non-legislative count for state jurisdiction', async () => {
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText(/Incluye.*15,000.*leyes de otros poderes/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 11. English labels
    // ---------------------------------------------------------------
    it('renders in English when lang is en', async () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'en', setLang: vi.fn() });
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText('Coverage by Jurisdiction')).toBeInTheDocument();
            expect(screen.getByText('State')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 12. Nahuatl labels
    // ---------------------------------------------------------------
    it('renders in Nahuatl when lang is nah', async () => {
        (useLang as ReturnType<typeof vi.fn>).mockReturnValue({ lang: 'nah', setLang: vi.fn() });
        mockGetStats.mockResolvedValue(MOCK_STATS);
        render(<JurisdictionCards />);

        await waitFor(() => {
            expect(screen.getByText('Tlanextīliztli Altepetl')).toBeInTheDocument();
            expect(screen.getByText('Altepetl')).toBeInTheDocument();
            expect(screen.getByText('Calpulli')).toBeInTheDocument();
        });
    });
});
