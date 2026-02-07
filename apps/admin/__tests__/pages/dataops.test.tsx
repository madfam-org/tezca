import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import DataOpsPage from '@/app/dataops/page';

vi.mock('next/link', () => ({
    default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

vi.mock('@tezca/ui', () => ({
    Button: ({ children, onClick, disabled, ...props }: React.PropsWithChildren<{ onClick?: () => void; disabled?: boolean }>) => (
        <button onClick={onClick} disabled={disabled} {...props}>{children}</button>
    ),
    Card: ({ children, ...props }: React.PropsWithChildren) => <div data-testid="card" {...props}>{children}</div>,
    CardContent: ({ children, ...props }: React.PropsWithChildren) => <div {...props}>{children}</div>,
}));

vi.mock('lucide-react', () => ({
    ArrowLeft: () => <span data-testid="arrow-left" />,
}));

const mockDashboardData = {
    coverage_views: {
        leyes_vigentes: { label: 'Leyes Vigentes', captured: 11904, universe: 12456, pct: 95.6 },
    },
    tier_progress: [],
    state_coverage: [],
    gap_summary: [],
    expansion_priorities: [],
    health_status: [],
};

vi.mock('@/lib/api', () => ({
    api: {
        getCoverageDashboard: vi.fn(),
    },
}));

vi.mock('@/components/dataops/CoverageHeader', () => ({
    CoverageHeader: ({ loading }: { loading: boolean }) => (
        <div data-testid="coverage-header">{loading ? 'Loading...' : 'Coverage Header'}</div>
    ),
}));

vi.mock('@/components/dataops/CoverageViewSelector', () => ({
    CoverageViewSelector: () => <div data-testid="coverage-view-selector">View Selector</div>,
}));

vi.mock('@/components/dataops/TierProgressList', () => ({
    TierProgressList: () => <div data-testid="tier-progress">Tier Progress</div>,
}));

vi.mock('@/components/dataops/StateCoverageTable', () => ({
    StateCoverageTable: () => <div data-testid="state-coverage">State Coverage</div>,
}));

vi.mock('@/components/dataops/GapSummaryPanel', () => ({
    GapSummaryPanel: () => <div data-testid="gap-summary">Gap Summary</div>,
}));

vi.mock('@/components/dataops/ExpansionPriorities', () => ({
    ExpansionPriorities: () => <div data-testid="expansion-priorities">Expansion Priorities</div>,
}));

vi.mock('@/components/dataops/HealthStatusGrid', () => ({
    HealthStatusGrid: () => <div data-testid="health-status">Health Status</div>,
}));

describe('DataOpsPage', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('renders back link to home', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getCoverageDashboard).mockReturnValue(new Promise(() => {}));

        render(<DataOpsPage />);
        const link = screen.getByText('Volver').closest('a');
        expect(link).toHaveAttribute('href', '/');
    });

    it('shows loading state initially', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getCoverageDashboard).mockReturnValue(new Promise(() => {}));

        render(<DataOpsPage />);
        expect(screen.getByTestId('coverage-header')).toHaveTextContent('Loading...');
    });

    it('renders dashboard components after loading', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getCoverageDashboard).mockResolvedValue(mockDashboardData);

        render(<DataOpsPage />);

        await waitFor(() => {
            expect(screen.getByTestId('coverage-header')).toHaveTextContent('Coverage Header');
        });

        expect(screen.getByTestId('tier-progress')).toBeInTheDocument();
        expect(screen.getByTestId('state-coverage')).toBeInTheDocument();
        expect(screen.getByTestId('gap-summary')).toBeInTheDocument();
        expect(screen.getByTestId('expansion-priorities')).toBeInTheDocument();
        expect(screen.getByTestId('health-status')).toBeInTheDocument();
    });

    it('shows error state with retry button', async () => {
        const { api } = await import('@/lib/api');
        vi.mocked(api.getCoverageDashboard).mockRejectedValue(new Error('Network error'));

        render(<DataOpsPage />);

        await waitFor(() => {
            expect(screen.getByText('Network error')).toBeInTheDocument();
        });

        expect(screen.getByText('Reintentar')).toBeInTheDocument();
    });
});
