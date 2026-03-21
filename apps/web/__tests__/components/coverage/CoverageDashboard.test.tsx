import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock @tezca/ui
vi.mock('@tezca/ui', () => ({
    Badge: ({ children, className }: any) => <span data-testid="badge" className={className}>{children}</span>,
    Button: ({ children, className, onClick, ...props }: any) => (
        <button className={className} onClick={onClick} {...props}>{children}</button>
    ),
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
    total_articles: 3500000,
    tiers: [
        {
            id: 'federal',
            name: { es: 'Federal', en: 'Federal', nah: 'Federal' },
            have: 2000,
            universe: 2500,
            pct: 80,
            color: 'green',
            confidence: 'high',
        },
        {
            id: 'state',
            name: { es: 'Estatal', en: 'State', nah: 'Altepetl' },
            have: 25000,
            universe: 35000,
            pct: 71,
            color: 'yellow',
            confidence: 'medium',
        },
        {
            id: 'noms',
            name: { es: 'NOMs', en: 'NOMs', nah: 'NOMs' },
            have: 428,
            universe: null,
            pct: null,
            color: 'red',
            confidence: 'low',
            note: { es: 'No existe censo', en: 'No census exists', nah: 'Ahmo' },
        },
        {
            id: 'municipal',
            name: { es: 'Municipal', en: 'Municipal', nah: 'Calpulli' },
            have: 3000,
            universe: null,
            pct: null,
            color: 'red',
            confidence: null,
            note: { es: 'Sin universo conocido', en: 'No known universe', nah: 'Ahmo machiz' },
        },
    ],
    coverage_views: {
        leyes_vigentes: {
            label: { es: 'Leyes Legislativas Vigentes', en: 'Active Legislative Laws', nah: 'Tenahuatilli' },
            universe: 12804,
            captured: 12804,
            pct: 100,
        },
        marco_juridico_completo: {
            label: { es: 'Marco Jurídico Completo', en: 'Complete Legal Framework', nah: 'Mochi' },
            universe: 36719,
            captured: 31846,
            pct: 86.7,
        },
        normatividad_primaria: {
            label: { es: 'Normatividad Primaria', en: 'Primary Legislation', nah: 'Achto' },
            universe: 36719,
            captured: 34285,
            pct: 93.4,
        },
        marco_juridico_total: {
            label: { es: 'Marco Jurídico Total', en: 'Total Legal Framework', nah: 'Cemānāhuac' },
            universe: 652136,
            captured: 35945,
            pct: 5.5,
        },
    },
    state_coverage: [
        { state: 'Jalisco', legislative: 500, non_legislative: 200, total: 700 },
        { state: 'Aguascalientes', legislative: 300, non_legislative: 100, total: 400 },
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
            // Both NOMs and Municipal have null pct
            const nds = screen.getAllByText('N/D');
            expect(nds.length).toBeGreaterThanOrEqual(2);
        });
    });

    // ---------------------------------------------------------------
    // 9. Shows "Desconocido" for unknown universe
    // ---------------------------------------------------------------
    it('shows "Desconocido" when universe is null', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            const unknowns = screen.getAllByText('Desconocido');
            expect(unknowns.length).toBeGreaterThanOrEqual(1);
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
            // "State" appears in both tier card and state table header
            expect(screen.getAllByText('State').length).toBeGreaterThanOrEqual(1);
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
            // "Altepetl" appears in both tier card name and state table header
            expect(screen.getAllByText('Altepetl').length).toBeGreaterThanOrEqual(1);
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

    // ---------------------------------------------------------------
    // 15. Coverage view tabs render
    // ---------------------------------------------------------------
    it('renders coverage view tabs', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('Perspectivas de cobertura')).toBeInTheDocument();
            // View label appears in both tab button and active detail card
            expect(screen.getAllByText(/Leyes Legislativas Vigentes/).length).toBeGreaterThanOrEqual(1);
        });
    });

    // ---------------------------------------------------------------
    // 16. State coverage table renders
    // ---------------------------------------------------------------
    it('renders state coverage table', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('Jalisco')).toBeInTheDocument();
            expect(screen.getByText('Aguascalientes')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 17. Confidence badges appear
    // ---------------------------------------------------------------
    it('renders confidence badges on tiers', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('alta')).toBeInTheDocument();
            expect(screen.getByText('media')).toBeInTheDocument();
            expect(screen.getByText('baja')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 18. Total articles displayed
    // ---------------------------------------------------------------
    it('displays total articles when present', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText(/3,500,000 artículos indexados/)).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 19. NOMs-like tier with null pct shows N/D
    // ---------------------------------------------------------------
    it('shows N/D for NOMs tier with null pct', async () => {
        mockGetCoverage.mockResolvedValue(MOCK_COVERAGE);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('NOMs')).toBeInTheDocument();
            expect(screen.getByText('No existe censo')).toBeInTheDocument();
        });
    });

    // ---------------------------------------------------------------
    // 20. No coverage views section when absent
    // ---------------------------------------------------------------
    it('does not render coverage view tabs when coverage_views is absent', async () => {
        const dataWithoutViews = { ...MOCK_COVERAGE, coverage_views: undefined };
        mockGetCoverage.mockResolvedValue(dataWithoutViews);
        render(<CoverageDashboard lang="es" />);

        await waitFor(() => {
            expect(screen.getByText('75%')).toBeInTheDocument();
        });
        expect(screen.queryByText('Perspectivas de cobertura')).not.toBeInTheDocument();
    });
});
