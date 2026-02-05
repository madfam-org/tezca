import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DashboardStatsGrid, RecentLawsList } from '@/components/DashboardStats';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
    api: {
        getStats: vi.fn(),
    },
}));

const mockStats = {
    total_laws: 11667,
    federal_count: 330,
    state_count: 11337,
    last_update: '2026-01-15',
    recent_laws: [
        { id: 'ley-1', name: 'Ley Federal de Test', date: '2026-01-10', tier: 'federal', category: 'ley' },
        { id: 'ley-2', name: 'Código Civil de Colima', date: '2025-06-01', tier: 'state', category: 'codigo' },
    ],
};

describe('DashboardStatsGrid', () => {
    beforeEach(() => {
        vi.mocked(api.getStats).mockReset();
    });

    it('shows loading skeleton initially', () => {
        vi.mocked(api.getStats).mockReturnValue(new Promise(() => {})); // never resolves
        const { container } = render(<DashboardStatsGrid />);

        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('renders stat cards after loading', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        render(<DashboardStatsGrid />);

        await waitFor(() => {
            expect(screen.getByText('11,667')).toBeInTheDocument();
        });

        expect(screen.getByText('330')).toBeInTheDocument();
        expect(screen.getByText('11,337')).toBeInTheDocument();
        expect(screen.getByText('Total de Leyes')).toBeInTheDocument();
        expect(screen.getByText('Federales')).toBeInTheDocument();
        expect(screen.getByText('Estatales')).toBeInTheDocument();
    });

    it('renders null when stats are null (API error)', async () => {
        vi.mocked(api.getStats).mockRejectedValue(new Error('API down'));

        const { container } = render(<DashboardStatsGrid />);

        await waitFor(() => {
            // After loading finishes with error, stats is null → renders null
            expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument();
        });
    });

    it('shows dash for null last_update', async () => {
        vi.mocked(api.getStats).mockResolvedValue({ ...mockStats, last_update: null });

        render(<DashboardStatsGrid />);

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
        const { container } = render(<RecentLawsList />);

        expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('renders recent law names', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        render(<RecentLawsList />);

        await waitFor(() => {
            expect(screen.getByText('Ley Federal de Test')).toBeInTheDocument();
        });

        expect(screen.getByText('Código Civil de Colima')).toBeInTheDocument();
    });

    it('shows correct tier labels', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        render(<RecentLawsList />);

        await waitFor(() => {
            expect(screen.getByText('Federal')).toBeInTheDocument();
        });

        expect(screen.getByText('Estatal')).toBeInTheDocument();
    });

    it('renders null when no recent laws', async () => {
        vi.mocked(api.getStats).mockResolvedValue({ ...mockStats, recent_laws: [] });

        const { container } = render(<RecentLawsList />);

        await waitFor(() => {
            expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument();
        });

        expect(screen.queryByText('Actualizaciones Recientes')).not.toBeInTheDocument();
    });

    it('links laws to their detail pages', async () => {
        vi.mocked(api.getStats).mockResolvedValue(mockStats);

        render(<RecentLawsList />);

        await waitFor(() => {
            const link = screen.getByText('Ley Federal de Test').closest('a');
            expect(link).toHaveAttribute('href', '/laws/ley-1');
        });
    });
});
