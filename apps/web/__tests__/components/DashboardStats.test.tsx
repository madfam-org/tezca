import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DashboardStatsGrid, RecentLawsList } from '@/components/DashboardStats';
import { LanguageProvider } from '@/components/providers/LanguageContext';
import { api } from '@/lib/api';

function renderWithLang(ui: React.ReactElement) {
    return render(<LanguageProvider>{ui}</LanguageProvider>);
}

vi.mock('@/lib/api', () => ({
    api: {
        getStats: vi.fn(),
    },
}));

const mockStats = {
    total_laws: 30343,
    federal_count: 333,
    state_count: 11363,
    municipal_count: 208,
    legislative_count: 11904,
    non_legislative_count: 18439,
    total_articles: 550000,
    federal_coverage: 99.1,
    state_coverage: 93.7,
    municipal_coverage: 0,
    total_coverage: 93.9,
    last_update: '2026-01-15',
    recent_laws: [
        { id: 'ley-1', name: 'Ley Federal de Test', date: '2026-01-10', tier: 'federal', category: 'ley' },
        { id: 'ley-2', name: 'Código Civil de Colima', date: '2025-06-01', tier: 'state', category: 'codigo' },
    ],
    coverage: {
        leyes_vigentes: {
            label: 'Leyes Legislativas Vigentes',
            count: 11696,
            universe: 12456,
            percentage: 93.9,
            description: 'Leyes federales + estatales del Poder Legislativo',
        },
        federal: {
            count: 333,
            universe: 336,
            percentage: 99.1,
            source: 'Cámara de Diputados',
            last_verified: '2026-02-03',
        },
        state: {
            count: 11363,
            universe: 12120,
            percentage: 93.7,
            source: 'OJN - Poder Legislativo',
            permanent_gaps: 782,
        },
        state_all_powers: {
            count: 11363,
            universe: 35780,
            percentage: 31.7,
            description: 'Incluye 23,660 leyes de otros poderes no descargadas aún',
        },
        municipal: {
            count: 208,
            universe: null,
            percentage: null,
            cities_covered: 5,
            total_municipalities: 2468,
            description: '208 leyes de 5 municipios',
        },
    },
};

describe('DashboardStatsGrid', () => {
    beforeEach(() => {
        vi.mocked(api.getStats).mockReset();
    });

    it('shows loading skeleton initially', () => {
        vi.mocked(api.getStats).mockReturnValue(new Promise(() => {})); // never resolves
        const { container } = renderWithLang(<DashboardStatsGrid />);

        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('renders stat cards after loading', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        renderWithLang(<DashboardStatsGrid />);

        await waitFor(() => {
            expect(screen.getByText('30,343')).toBeInTheDocument();
        });

        expect(screen.getByText('333')).toBeInTheDocument();
        expect(screen.getByText('11,363')).toBeInTheDocument();
        expect(screen.getByText('Total de Leyes')).toBeInTheDocument();
        expect(screen.getByText('Federales')).toBeInTheDocument();
        expect(screen.getByText('Estatales')).toBeInTheDocument();
    });

    it('renders null when stats are null (API error)', async () => {
        vi.mocked(api.getStats).mockRejectedValue(new Error('API down'));

        const { container } = renderWithLang(<DashboardStatsGrid />);

        await waitFor(() => {
            // After loading finishes with error, stats is null → renders null
            expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument();
        });
    });

    it('shows dash for null last_update', async () => {
        vi.mocked(api.getStats).mockResolvedValue({ ...mockStats, last_update: null });

        renderWithLang(<DashboardStatsGrid />);

        await waitFor(() => {
            expect(screen.getByText('-')).toBeInTheDocument();
        });
    });
});

describe('RecentLawsList', () => {
    beforeEach(() => {
        vi.mocked(api.getStats).mockReset();
    });

    it('shows loading skeleton initially', () => {
        vi.mocked(api.getStats).mockReturnValue(new Promise(() => {}));
        const { container } = renderWithLang(<RecentLawsList />);

        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('renders recent law names', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        renderWithLang(<RecentLawsList />);

        await waitFor(() => {
            expect(screen.getByText('Ley Federal de Test')).toBeInTheDocument();
        });

        expect(screen.getByText('Código Civil de Colima')).toBeInTheDocument();
    });

    it('shows correct tier labels', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        renderWithLang(<RecentLawsList />);

        await waitFor(() => {
            expect(screen.getByText('Federal')).toBeInTheDocument();
        });

        expect(screen.getByText('Estatal')).toBeInTheDocument();
    });

    it('renders null when no recent laws', async () => {
        vi.mocked(api.getStats).mockResolvedValue({ ...mockStats, recent_laws: [] });

        const { container } = renderWithLang(<RecentLawsList />);

        await waitFor(() => {
            expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument();
        });

        expect(screen.queryByText('Actualizaciones Recientes')).not.toBeInTheDocument();
    });

    it('links laws to their detail pages', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        renderWithLang(<RecentLawsList />);

        await waitFor(() => {
            const link = screen.getByText('Ley Federal de Test').closest('a');
            expect(link).toHaveAttribute('href', '/leyes/ley-1');
        });
    });
});
