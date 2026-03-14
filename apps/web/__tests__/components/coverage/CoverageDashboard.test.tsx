import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Card: ({ children, className }: any) => <div data-testid="card" className={className}>{children}</div>,
    CardContent: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

const mockGetCoverage = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        getCoverage: (...args: any[]) => mockGetCoverage(...args),
    },
}));

import { CoverageDashboard } from '@/components/coverage/CoverageDashboard';

const MOCK_COVERAGE = {
    total_laws: 35000,
    total_items: 30000,
    total_universe: 40000,
    overall_pct: 75,
    tiers: [
        {
            id: 'federal',
            name: { es: 'Federal', en: 'Federal', nah: 'Federal' },
            have: 2000,
            universe: 2500,
            pct: 80,
            color: 'green',
        },
        {
            id: 'state',
            name: { es: 'Estatal', en: 'State', nah: 'Altepetl' },
            have: 25000,
            universe: 35000,
            pct: 71,
            color: 'yellow',
        },
        {
            id: 'municipal',
            name: { es: 'Municipal', en: 'Municipal', nah: 'Calpulli' },
            have: 3000,
            universe: null,
            pct: null,
            color: 'red',
            note: { es: 'Sin universo conocido', en: 'No known universe', nah: 'Ahmo machiz' },
        },
    ],
    last_updated: '2026-03-01',
};

describe('CoverageDashboard', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    // ---------------------------------------------------------------
    // 1. Shows loading state
    // ---------------------------------------------------------------
    it('shows loading state while data is fetching', () => {
        mockGetCoverage.mockReturnValue(new Promise(() => {})); // Never resolves
        render(<CoverageDashboard lang="es" />);

        expect(screen.getByText('Cargando estadísticas...')).toBeInTheDocument();
    });

    // ---------------------------------------------------------------
    // 2. Shows error state on API failure
    // ---------------------------------------------------------------
    it('shows error message when API fails', async () => {
        mockGetCoverage.mockRejectedValue(new Error('Network error'));
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('No se pudieron cargar las estadísticas')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 3. Renders overall coverage percentage
    // ---------------------------------------------------------------
    it('renders overall coverage percentage', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('75%')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 4. Renders overall title
    // ---------------------------------------------------------------
    it('renders overall title in Spanish', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('Cobertura general')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 5. Renders total laws count
    // ---------------------------------------------------------------
    it('displays total laws in database', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText(/Leyes en base de datos.*35,000/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 6. Renders per-tier cards
    // ---------------------------------------------------------------
    it('renders all tier cards', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('Federal')).toBeInTheDocument();
            expect(screen.getByText('Estatal')).toBeInTheDocument();
            expect(screen.getByText('Municipal')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 7. Shows tier percentage
    // ---------------------------------------------------------------
    it('shows tier percentage for tiers with pct', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('80%')).toBeInTheDocument();
            expect(screen.getByText('71%')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 8. Shows N/D for tiers without percentage
    // ---------------------------------------------------------------
    it('shows N/D for tiers with null percentage', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('N/D')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 9. Shows "Desconocido" for unknown universe
    // ---------------------------------------------------------------
    it('shows "Desconocido" when universe is null', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('Desconocido')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 10. Renders tier notes
    // ---------------------------------------------------------------
    it('renders tier notes when present', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('Sin universo conocido')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 11. Renders last updated timestamp
    // ---------------------------------------------------------------
    it('renders last updated timestamp', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText(/2026-03-01/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 12. Renders in English
    // ---------------------------------------------------------------
    it('renders labels in English when lang is en', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="en" />);

        await waitFor(() => {
            expect(screen.getByText('Overall coverage')).toBeInTheDocument();
            expect(screen.getByText('State')).toBeInTheDocument();
            expect(screen.getByText(/Last updated/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 13. Renders in Nahuatl
    // ---------------------------------------------------------------
    it('renders labels in Nahuatl when lang is nah', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="nah" />);

        await waitFor(() => {
            expect(screen.getByText('Mochi cobertura')).toBeInTheDocument();
            expect(screen.getByText('Altepetl')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 14. Loading state in English
    // ---------------------------------------------------------------
    it('shows English loading text when lang is en', () => {
        mockGetCoverage.mockReturnValue(new Promise(() => {}));
        render(<CoverageDashboard lang="en" />);

        expect(screen.getByText('Loading statistics...')).toBeInTheDocument();
    });
});
